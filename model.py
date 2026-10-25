# Copyright (c) 2026 the repository owner. All rights reserved. See LICENSE.
"""Mary Mount Economy Lab. Annual flows; stocks advance in fractions of a year.

This is an original, deliberately small synthesis, not a replication of any
author's model. See theory.html for the equations, institutional boundary,
transaction matrix, source map and unvalidated behavioural assumptions.
Only the Python standard library is required.
"""
import math

VERSION = "2.0.0"
# name, default, minimum, maximum, display unit, group, explanation
SPECS = [
    ("years", 15, 1, 40, "years", "Run", "Simulation and conditional valuation horizon."),
    ("dt", .125, .03125, .25, "years", "Run", "Accounting time step. 0.125 = eight periods per year."),
    ("alpha", .35, .05, .8, "fraction", "Capacity", "Capital elasticity of capacity; not the profit share."),
    ("depreciation", .05, 0, .25, "% / year", "Capacity", "Private and public physical capital depreciation."),
    ("private_capital", 240, 20, 1000, "GDP₀ units", "Opening stocks", "Real private capital; initial annual real GDP is normalised to about 100."),
    ("public_capital", 60, 0, 500, "GDP₀ units", "Opening stocks", "Real public capital; its services enter capacity."),
    ("public_efficiency", 1, 0, 2, "multiple", "Capacity", "Effective capacity services per unit of public capital; an assumption."),
    ("labour", 100, 1, 1000, "index", "Opening stocks", "Population index; participation, retirement and paid hours determine effective labour."),
    ("population_growth", .005, -.03, .05, "% / year", "Capacity", "Population growth, separate from participation, ageing and paid hours; no endogenous fertility or migration theory."),
    ("productivity_growth", .012, -.03, .07, "% / year", "Capacity", "Hicks-neutral productivity growth, separate from population."),
    ("normal_utilisation", .95, .6, 1, "fraction", "Capacity", "Normal actual output relative to capacity; calibration anchor."),
    ("profit_share", .35, .12, .65, "fraction", "Distribution", "Gross operating surplus share before depreciation, interest and corporate tax."),
    ("wage_delay", 3, .125, 15, "years", "Distribution", "Delay for the operating surplus share to approach its target."),
    ("worker_mpc", .9, .2, .98, "fraction", "Distribution", "Workers' consumption out of current disposable income."),
    ("owner_mpc", .5, .1, .95, "fraction", "Distribution", "Owners' consumption out of dividends, bank distributions and transfers."),
    ("wealth_mpc", .0093, 0, .08, "% / year", "Distribution", "Consumption out of opening deposits. Equity gains are excluded."),
    ("payout", .5, 0, 1, "fraction", "Distribution", "Distributed share of positive net corporate earnings."),
    ("wage_tax", .2, 0, .6, "fraction", "Fiscal policy", "Tax on the wage bill; separate from the corporate tax."),
    ("corporate_tax", .2, 0, .5, "fraction", "Fiscal policy", "Tax on positive profits after depreciation and net interest."),
    ("government_share", .2, 0, .5, "fraction of GDP₀", "Fiscal policy", "Government purchases at t=0; excludes transfers and interest."),
    ("transfer_share", .05, 0, .25, "fraction of GDP₀", "Fiscal policy", "Transfers at t=0; disposable income, not an additional GDP component."),
    ("worker_transfer_fraction", .8, 0, 1, "fraction", "Fiscal policy", "Recipient mix: workers' share of transfers. Owners receive the remainder."),
    ("public_investment_fraction", .15, 0, 1, "fraction", "Fiscal policy", "Share of government purchases that forms public capital; counted in G once."),
    ("fiscal_real_growth", .025, -.05, .08, "% / year", "Fiscal policy", "Real trend growth of purchases and transfers."),
    ("debt_tax_response", .08, 0, .3, "% / year", "Fiscal policy", "Additional owner tax per unit of government debt above the debt/GDP target. Zero gives an accommodating fiscal closure."),
    ("debt_target", .8, 0, 3, "fraction of GDP", "Fiscal policy", "Debt ratio used by the hypothetical owner-tax stabiliser; not an observed policy rule."),
    ("net_export_share", 0, -.15, .15, "fraction of GDP₀", "External sector", "Net exports level grows at the fiscal real trend. No FX or foreign income."),
    ("government_debt", 80, 0, 300, "GDP₀ units", "Opening stocks", "Consolidated government bills, all held by the model bank."),
    ("firm_net_debt", 120, -100, 400, "GDP₀ units", "Opening stocks", "Business loans less business deposits; may turn negative as firms accumulate cash."),
    ("net_foreign_assets", 0, -100, 200, "GDP₀ units", "Opening stocks", "Bank net foreign settlement asset; no interest or exchange-rate revaluation."),
    ("worker_wealth_fraction", .3, .05, .95, "fraction", "Opening stocks", "Workers' share of opening household deposits; equity ownership is specified separately."),
    ("investment_share", .2, .02, .4, "fraction of GDP₀", "Investment & credit", "Initial private investment and normal investment propensity."),
    ("investment_delay", 2, .125, 10, "years", "Investment & credit", "Investment adjusts toward its desired level with this delay."),
    ("interest_sensitivity", 4, 0, 15, "coefficient", "Investment & credit", "Desired investment semi-elasticity to the real lending / natural rate gap."),
    ("accelerator", .5, 0, 3, "coefficient", "Investment & credit", "Desired investment response to utilisation relative to normal."),
    ("credit_spread", .01, 0, .15, "% / year", "Investment & credit", "Borrowing spread over the policy rate; explicit credit-availability proxy."),
    ("natural_rate", .02, -.02, .1, "% real / year", "Monetary policy", "Unobserved Wicksell-inspired investment hurdle; an assumption, not an identity or measured r-star."),
    ("policy_base", .03, -.01, .15, "% nominal / year", "Monetary policy", "Initial policy rate and anchor for the optional reaction rule."),
    ("inflation_target", .02, -.02, .1, "% / year", "Monetary policy", "Initial expected inflation and target for the optional policy rule."),
    ("price_response", .12, 0, 1, "coefficient", "Monetary policy", "Inflation response to excess utilisation. Price changes do not erase goods-market accounting."),
    ("expectation_delay", 3, .125, 15, "years", "Monetary policy", "Adaptive inflation expectations delay."),
    ("expectation_anchor", .75, 0, 1, "fraction", "Monetary policy", "Weight on the inflation target in expectations; zero gives purely adaptive expectations."),
    ("policy_delay", 1, .125, 8, "years", "Monetary policy", "Speed at which the policy rate follows its target."),
    ("policy_inflation_response", 1.5, 0, 4, "coefficient", "Monetary policy", "Policy target response to inflation above target; zero disables this channel."),
    ("policy_gap_response", .3, 0, 2, "coefficient", "Monetary policy", "Policy response to excess utilisation; zero disables this channel."),
    ("sentiment_target", 0, -2, 2, "index", "Valuation", "Exogenous sentiment target; moves ERP, not an accounting resource."),
    ("sentiment_delay", 2, .125, 10, "years", "Valuation", "Delay for sentiment to approach its target."),
    ("sentiment_erp", .25, 0, 1, "coefficient", "Valuation", "ERP multiplier is exp(-coefficient × sentiment)."),
    ("equity_premium", .045, .005, .15, "% / year", "Valuation", "Nominal equity risk premium above the risk-free yield proxy."),
    ("term_premium", .01, -.02, .06, "% / year", "Valuation", "Long-yield proxy = current policy rate + this term spread; not a term-structure model."),
    ("terminal_growth", .03, -.02, .08, "% nominal / year", "Valuation", "Perpetual earnings growth after the explicit horizon."),
    ("terminal_risk_free", .04, -.01, .15, "% nominal / year", "Valuation", "Normalised perpetual risk-free rate; separate from the last simulated policy rate."),
    ("terminal_equity_premium", .045, .005, .15, "% / year", "Valuation", "Normalised perpetual equity premium; separate from temporary sentiment."),
    ("terminal_roe", .12, .01, .4, "% / year", "Valuation", "Terminal return on equity; sustainable payout = 1 - growth / ROE."),
]
SPECS += [
    ('weekly_hours',40,10,65,'hours / week','Work & households','Opening paid hours per employed worker; unpaid care and travel excluded.'),
    ('hours_income_effect',.25,0,1,'elasticity','Work & households','A higher real net wage permits less work; preference assumption, not a universal law.'),
    ('hours_substitution_effect',.15,0,1,'elasticity','Work & households','A higher real net wage makes leisure more costly and can increase work.'),
    ('hours_adjustment',2,.125,10,'years','Work & households','Delay for desired weekly hours.'),
    ('maximum_hours',60,15,70,'hours / week','Work & households','Explicit work-time ceiling; unmet essential needs are reported.'),
    ('essential_consumption_share',.3,0,.65,'fraction of GDP₀','Work & households','Real essential basket for wage-dependent households at the opening date.'),
    ('aspiration_growth',0,-.02,.04,'% / year','Work & households','Growth in the desired standard of living; zero permits a sufficiency experiment.'),
    ('wealth_leisure_effect',0,0,1,'coefficient','Work & households','Additional preference for leisure as real net liquid wealth rises above its opening level.'),
    ('household_debt',0,0,150,'GDP₀ units','Opening stocks','Opening wage-household debt, with a matching bank asset and deposits.'),
    ('household_credit_growth',0,-.05,.15,'% nominal / year','Investment & credit','Net household borrowing relative to its opening debt stock each year.'),
    ('household_credit_spread',.03,0,.2,'% / year','Investment & credit','Household borrowing spread above the policy rate.'),
    ('credit_consumption_fraction',1,0,1,'fraction','Investment & credit','Share of new household borrowing initially spent rather than held as deposits.'),
    ('retired_fraction',.2,.05,.5,'fraction','Demography','Opening retired population share; wage households and owners are not age cohorts.'),
    ('ageing_trend',0,-.01,.015,'fraction / year','Demography','Annual change in the retired share; paths crossing 2–65% are rejected.'),
    ('participation',.8,.3,.95,'fraction','Demography','Working-age labour-force participation.'),
    ('pension_share',0,0,.15,'fraction of GDP₀','Demography','Initial pensions, scaling with retiree numbers and the price level; separate from other transfers.'),
    ('pension_worker_fraction',.2,0,1,'fraction','Demography','Pension receipts allocated to wage-dependent households; remainder to asset households.'),
    ('land_rent_share',0,0,.2,'fraction of GDP','Land & ownership','Land income within gross operating surplus; removed before corporate EBITDA.'),
    ('land_tax',0,0,1,'fraction','Land & ownership','Tax on private land rent, with a government receipt counterpart.'),
    ('land_cap_rate',.04,.01,.2,'% / year','Land & ownership','Capitalisation rate for net land rents; an assumed yield, not an observed land valuation.'),
    ('worker_equity_fraction',0,0,.9,'fraction','Land & ownership','Opening worker ownership of business equity; held fixed through a run.'),
    ('public_equity_fraction',0,0,.9,'fraction','Land & ownership','Opening public ownership of business equity; dividends reduce the fiscal deficit.'),
    ('worker_land_fraction',0,0,.9,'fraction','Land & ownership','Opening worker share of total land ownership; held fixed through a run.'),
    ('public_land_fraction',0,0,1,'fraction','Land & ownership','Public land ownership; public rents enter the government account.'),
    ('worker_bank_fraction',0,0,1,'fraction','Land & ownership','Initial allocation of bank distributions between the two household groups.'),
    ('wealth_tax',0,0,.06,'% / year','Fiscal policy','Tax on positive net liquid household wealth; no tax on a hypothetical future DCF mark.'),
    ('innovation_share',0,0,.5,'fraction','Innovation','Share of private investment forming knowledge rather than physical capital; counted in I once.'),
    ('innovation_success',.5,0,1,'fraction','Innovation','Assumed successful share of research capital; this is an expected-value experiment.'),
    ('innovation_efficiency',.2,0,.8,'% / year','Innovation','Productivity spillover per unit of knowledge / total private capital.'),
    ('reserve_backing',0,0,1,'fraction','Money institutions','Public reserve backing of deposits. Reserves are funded by matched Treasury credit; this is a limited public-credit closure.'),
    ('cancel_public_bonds',0,0,1,'fraction','Money institutions','Opening bank-held bills offset against Treasury credit; reclassification, not new net wealth.'),
    ('treasury_funding_spread',0,-.01,.08,'% / year','Money institutions','Treasury credit charges policy rate plus this spread. Funding remains accommodating.'),
    ('reserve_remuneration',0,0,.1,'% / year','Money institutions','Interest paid by government on locked reserve backing.'),
    ('sovereign_spread',0,0,.1,'% / year','External sector','Domestic-currency sovereign funding spread; no automatic exchange-rate collapse rule.'),
]
SCHEMA = {s[0]: dict(default=s[1], minimum=s[2], maximum=s[3], unit=s[4], group=s[5], help=s[6]) for s in SPECS}
DEFAULTS = {k: s['default'] for k, s in SCHEMA.items()}
INITIAL = {'years','dt','private_capital','public_capital','labour','government_debt','firm_net_debt','net_foreign_assets','worker_wealth_fraction'}
INITIAL |= {'household_debt','weekly_hours','retired_fraction','worker_equity_fraction','public_equity_fraction','worker_land_fraction','public_land_fraction','worker_bank_fraction','reserve_backing','cancel_public_bonds'}


class ModelError(ValueError):
    pass


def validate(config):
    if not isinstance(config, dict):
        raise ModelError('Parameters must be a JSON object.')
    unknown = set(config) - set(DEFAULTS)
    if unknown:
        raise ModelError('Unknown parameters: ' + ', '.join(sorted(unknown)))
    p = dict(DEFAULTS, **config)
    for k, v in p.items():
        s = SCHEMA[k]
        if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v):
            raise ModelError(k + ' must be a finite number.')
        if not s['minimum'] <= v <= s['maximum']:
            raise ModelError(f"{k} must be between {s['minimum']} and {s['maximum']} ({s['unit']}).")
    if p['years'] / p['dt'] > 1280:
        raise ModelError('Use at most 1280 steps; increase the time step or reduce the horizon.')
    if abs(p['years']/p['dt'] - round(p['years']/p['dt'])) > 1e-7:
        raise ModelError('The horizon must be a whole number of time steps.')
    if p['worker_equity_fraction']+p['public_equity_fraction']>1:
        raise ModelError('Worker and public equity ownership cannot sum to more than 100%.')
    if p['land_rent_share']>=p['profit_share']:
        raise ModelError('Land rent must be below the operating surplus share.')
    if p['weekly_hours']>p['maximum_hours']:
        raise ModelError('Opening hours cannot exceed the work-time ceiling.')
    D=p['government_debt']+p['firm_net_debt']+p['net_foreign_assets']+p['household_debt']
    if p['cancel_public_bonds']*p['government_debt']>p['reserve_backing']*D+1e-8:
        raise ModelError('The opening bill offset cannot exceed available matched Treasury credit.')
    if D <= 0:
        raise ModelError('Opening household deposits (government bills + firm net debt + foreign assets) must be positive.')
    return p


def validate_shocks(shocks, p):
    if not isinstance(shocks, list) or len(shocks) > 12:
        raise ModelError('Use a list of at most 12 shocks.')
    clean = []
    for x in shocks:
        if not isinstance(x, dict) or set(x) - {'parameter','amount','start','end','shape'}:
            raise ModelError('Each shock uses parameter, amount, start, end and shape.')
        key = x.get('parameter')
        if key not in DEFAULTS or key in INITIAL:
            raise ModelError('Shock parameter must be a behavioural parameter, not an opening stock or run setting.')
        shape = x.get('shape', 'step')
        if shape not in ('step','pulse','ramp'):
            raise ModelError('Shock shape must be step, pulse or ramp.')
        start, end, amount = x.get('start', 2), x.get('end', 5), x.get('amount', 0)
        if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in (start,end,amount)):
            raise ModelError('Shock times and amounts must be finite numbers.')
        if not 0 <= start < p['years']:
            raise ModelError('A shock must start at or after zero and before the horizon.')
        if shape != 'step' and not start < end <= p['years']:
            raise ModelError('A pulse or ramp must satisfy start < end ≤ horizon.')
        required_times=[start] if shape=='step' else [start,end]
        if any(abs(t/p['dt']-round(t/p['dt']))>1e-7 for t in required_times):
            raise ModelError('Shock dates must align with the selected time step; no event date is silently rounded.')
        clean.append(dict(parameter=key,amount=amount,start=start,end=end,shape=shape))
    # Test combined overlaps, including the last pre-end value for pulses.
    times = {0, p['years']}
    for x in clean:
        times.update((x['start'], x['end'], max(x['start'],x['end']-1e-8)))
    for t in times:
        validate(effective(p,clean,t))
    return clean


def effective(p, shocks, t):
    out = dict(p)
    for x in shocks:
        if t < x['start']:
            continue
        weight = 1
        if x['shape'] == 'pulse' and t >= x['end']:
            weight = 0
        elif x['shape'] == 'ramp':
            weight = min(1,(t-x['start'])/(x['end']-x['start']))
        out[x['parameter']] += x['amount'] * weight
    return out


def relaxation(current, target, dt, delay):
    return target + (current-target)*math.exp(-dt/delay)


def flows(p, state, t, capacity, opening=None):
    opening=opening or p
    P,K,J,L,A,B,Q,N,Dw,Do,I,pe,rate,theta,S,h,H,knowledge,retired = state
    if not .02 <= retired <= .65:
        raise ModelError(f'Year {t:g}: the retired share left the stated 2–65% demographic domain.')
    trend=math.exp(p['fiscal_real_growth']*t)
    G=100*p['government_share']*trend*P
    general_transfers=100*p['transfer_share']*trend*P
    pension=100*p['pension_share']*(L/opening['labour'])*(retired/opening['retired_fraction'])*P
    Tr=general_transfers+pension
    transfer_w=p['worker_transfer_fraction']*general_transfers+p['pension_worker_fraction']*pension
    transfer_o=Tr-transfer_w
    NX=100*p['net_export_share']*trend*P
    Ip=I*P
    dep=p['depreciation']*(K+knowledge)*P
    interest_f=rate*Q+(p['credit_spread']+p['sovereign_spread'])*max(Q,0)
    interest_h=(rate+p['household_credit_spread'])*H
    interest_g=(rate+p['sovereign_spread'])*B
    reserves=p['reserve_backing']*(Dw+Do)
    offset=opening['cancel_public_bonds']*opening['government_debt']
    treasury=reserves-offset
    if treasury < -1e-7:
        raise ModelError('Treasury funding has been repaid beyond this closure. Add a replacement funding rule or shorten the run.')
    interest_t=(rate+p['treasury_funding_spread'])*treasury
    interest_r=p['reserve_remuneration']*reserves
    bank_distribution=interest_f+interest_h+interest_g+interest_r-interest_t
    bank_w=p['worker_bank_fraction']*bank_distribution
    bank_o=bank_distribution-bank_w
    borrowing=p['household_credit_growth']*H
    wealth_tax_w=p['wealth_tax']*max(0,Dw-H)
    wealth_tax_o=p['wealth_tax']*max(0,Do)

    def at(Y):
        wage=(1-theta)*Y
        rent=p['land_rent_share']*Y
        gross_surplus=theta*Y-rent
        if gross_surplus<0:
            raise ModelError('Land rent exceeds the current operating-surplus allocation; reconcile the distribution assumptions.')
        rent_public=p['public_land_fraction']*rent
        private_rent=rent-rent_public
        tax_land=p['land_tax']*private_rent
        rent_w=p['worker_land_fraction']*rent*(1-p['land_tax'])
        rent_o=private_rent-tax_land-rent_w
        tax_w=p['wage_tax']*wage
        tax_f=p['corporate_tax']*max(0,gross_surplus-dep-interest_f)
        tax_o=p['debt_tax_response']*max(0,B-p['debt_target']*Y)
        earnings=gross_surplus-dep-interest_f-tax_f
        dividend=p['payout']*max(0,earnings)
        div_w=p['worker_equity_fraction']*dividend
        div_g=p['public_equity_fraction']*dividend
        div_o=dividend-div_w-div_g
        yd_w=wage-tax_w+transfer_w+div_w+rent_w+bank_w-interest_h-wealth_tax_w
        yd_o=div_o+bank_o+transfer_o+rent_o-tax_o-wealth_tax_o
        cw=max(0,p['worker_mpc']*yd_w+p['wealth_mpc']*max(Dw-H,0)+p['credit_consumption_fraction']*borrowing)
        co=max(0,p['owner_mpc']*yd_o+p['wealth_mpc']*max(Do,0))
        return dict(wages=wage,gross_surplus=gross_surplus,tax_w=tax_w,tax_f=tax_f,tax_o=tax_o,
                    earnings=earnings,dividend=dividend,div_w=div_w,div_o=div_o,div_g=div_g,
                    rent=rent,rent_w=rent_w,rent_o=rent_o,rent_public=rent_public,tax_land=tax_land,
                    yd_w=yd_w,yd_o=yd_o,cw=cw,co=co)

    def gap(Y):
        f=at(Y)
        return Y-f['cw']-f['co']-Ip-G-NX
    low,high=0.,100*P
    if gap(0)>=0:
        raise ModelError(f'Year {t:g}: no positive goods-market solution. Check net exports, debt service and demand assumptions.')
    for _ in range(60):
        if gap(high)>0:break
        high*=2
    else:raise ModelError('No finite goods-market solution for this consumption closure.')
    for _ in range(65):
        mid=(low+high)/2
        if gap(mid)>0:high=mid
        else:low=mid
    Y=(low+high)/2;f=at(Y)
    sf=f['gross_surplus']-interest_f-f['tax_f']-f['dividend']
    revenues=f['tax_w']+f['tax_f']+f['tax_o']+wealth_tax_w+wealth_tax_o+f['tax_land']+f['rent_public']+f['div_g']+interest_t
    deficit=G+Tr+interest_g+interest_r-revenues
    sw,so=f['yd_w']-f['cw'],f['yd_o']-f['co']
    real_y=Y/P;util=real_y/capacity
    inflation=pe+p['price_response']*(util/p['normal_utilisation']-1)
    loan_rate=rate+p['credit_spread']+p['sovereign_spread']
    real_loan=(1+loan_rate)/(1+pe)-1
    workforce=L*((1-retired)/(1-DEFAULTS['retired_fraction']))*(p['participation']/DEFAULTS['participation'])
    employment=min(1.,util/p['normal_utilisation'])
    paid_workers=workforce*employment
    net_hourly=(f['wages']/P)*(1-p['wage_tax'])/(paid_workers*h)
    reference_hourly=(1-DEFAULTS['profit_share'])*100*(1-DEFAULTS['wage_tax'])/(opening['labour']*DEFAULTS['weekly_hours'])
    wage_ratio=net_hourly/reference_hourly
    net_worker_wealth=(Dw-H)/P
    initial_worker_wealth=(opening['government_debt']+opening['firm_net_debt']+opening['net_foreign_assets']+opening['household_debt'])*opening['worker_wealth_fraction']-opening['household_debt']
    wealth_gain=max(0,(net_worker_wealth-initial_worker_wealth)/100)
    preferred_hours=opening['weekly_hours']*wage_ratio**(p['hours_substitution_effect']-p['hours_income_effect'])*math.exp(p['aspiration_growth']*t)/(1+p['wealth_leisure_effect']*wealth_gain)
    essential=100*p['essential_consumption_share']*(L/opening['labour'])*math.exp(p['aspiration_growth']*t)
    nonwage=(transfer_w+f['div_w']+f['rent_w']+bank_w-interest_h-wealth_tax_w)/P
    required_hours=max(0,essential-nonwage+max(-borrowing,0)/P)/(net_hourly*paid_workers)
    target_hours=min(p['maximum_hours'],max(preferred_hours,required_hours))
    f.update(t=t,price=P,real_gdp=real_y,nominal_gdp=Y,capacity=capacity,utilisation=util,
             inflation=inflation,expected_inflation=pe,policy_rate=rate,loan_rate=loan_rate,
             real_lending_rate=real_loan,natural_rate=p['natural_rate'],rate_gap=real_loan-p['natural_rate'],
             government=G,transfers=Tr,general_transfers=general_transfers,pensions=pension,
             transfer_w=transfer_w,transfer_o=transfer_o,net_exports=NX,investment=Ip,
             public_investment=p['public_investment_fraction']*G,depreciation=dep,
             firm_interest=interest_f,household_interest=interest_h,government_interest=interest_g,
             treasury_interest=interest_t,reserve_interest=interest_r,bank_distribution=bank_distribution,
             bank_w=bank_w,bank_o=bank_o,wealth_tax_w=wealth_tax_w,wealth_tax_o=wealth_tax_o,
             worker_saving=sw,owner_saving=so,firm_saving=sf,firm_net_lending=sf-Ip,
             government_balance=-deficit,foreign_balance=-NX,deficit=deficit,
             private_capital=K,public_capital=J,knowledge_capital=knowledge,labour=L,productivity=A,
             government_debt=B,firm_net_debt=Q,household_debt=H,household_borrowing=borrowing,
             net_foreign_assets=N,worker_deposits=Dw,owner_deposits=Do,deposits=Dw+Do,
             worker_net_liquid_wealth=Dw-H,sentiment=S,debt_gdp=B/Y,
             public_net_liability_gdp=(B+reserves-treasury)/Y,profit_share=theta,
             risk_free_yield=rate+p['term_premium']+p['sovereign_spread'],
             cost_of_equity=rate+p['term_premium']+p['sovereign_spread']+p['equity_premium']*math.exp(-p['sentiment_erp']*S),
             weekly_hours=h,desired_hours=target_hours,preferred_hours=preferred_hours,required_hours=required_hours,
             leisure_hours=112-h,net_hourly_wage_index=wage_ratio*100,workforce=workforce,employment_ratio=employment,
             effective_labour=workforce*h/DEFAULTS['weekly_hours'],retired_fraction=retired,
             old_age_dependency=retired/((1-retired)*p['participation']*employment),
             pension_payroll_ratio=pension/f['wages'] if f['wages'] else 0,
             household_service_ratio=interest_h/f['wages'] if f['wages'] else 0,
             essential_shortfall=max(0,essential-f['cw']/P),
             reserves=reserves,treasury_funding=treasury,reserve_backing=p['reserve_backing'],
             worker_equity_fraction=p['worker_equity_fraction'],public_equity_fraction=p['public_equity_fraction'],
             worker_land_value=f['rent_w']/p['land_cap_rate'],owner_land_value=f['rent_o']/p['land_cap_rate'],
             public_land_value=f['rent_public']/p['land_cap_rate'])
    f['goods_residual']=Y-f['cw']-f['co']-Ip-G-NX
    f['sector_residual']=sw+so+(sf-Ip)-deficit-NX
    f['bank_residual']=B+Q+H+N+reserves-treasury-Dw-Do
    return f


def valuation(rows, p, shocks, rate_shift=0, growth_shift=0):
    last=rows[-1]
    end=effective(p,shocks,last['t'])
    g=end['terminal_growth']+growth_shift
    roe=end['terminal_roe']
    r=end['terminal_risk_free']+end['terminal_equity_premium']+rate_shift
    if g < 0:
        return None, 'Terminal growth is negative: this steady-state retention closure needs a separate liquidation model.'
    if g >= roe:
        return None, 'Terminal growth must be below terminal ROE to leave a positive sustainable payout.'
    if r <= g:
        return None, 'Terminal cost of equity must exceed terminal nominal growth. No denominator floor is applied.'
    if last['earnings'] <= 0:
        return None, 'Terminal earnings are non-positive; a recovery or liquidation model is required.'
    payout=1-g/roe
    value=last['earnings']*(1+g)*payout/(r-g)
    values=[0.]*len(rows)
    values[-1]=value
    for i in range(len(rows)-2,-1,-1):
        dt=rows[i+1]['t']-rows[i]['t']
        rr=rows[i]['cost_of_equity']+rate_shift
        if rr <= -1:
            return None, 'A discount rate must exceed -100%.'
        value=(rows[i]['dividend']*dt+value)/(1+rr)**dt
        values[i]=value
    terminal_pv=values[-1]
    for i in range(len(rows)-1):
        terminal_pv/=(1+rows[i]['cost_of_equity']+rate_shift)**(rows[i+1]['t']-rows[i]['t'])
    return dict(values=values,value=values[0],terminal_payout=payout,
                terminal_share=terminal_pv/values[0] if values[0] else None,
                terminal_growth=g,terminal_cost=r), None


def simulate(config=None, shocks=None):
    p=validate({} if config is None else config)
    shocks=validate_shocks([] if shocks is None else shocks,p)
    dt=p['dt'];n=round(p['years']/dt)
    D=p['government_debt']+p['firm_net_debt']+p['net_foreign_assets']+p['household_debt']
    K0=p['private_capital'];J0=p['public_capital'];L0=p['labour']
    effective_k0=K0+p['public_efficiency']*J0
    offset=p['cancel_public_bonds']*p['government_debt']
    state=[1.,K0,J0,L0,1.,p['government_debt']-offset,p['firm_net_debt'],p['net_foreign_assets'],
           D*p['worker_wealth_fraction'],D*(1-p['worker_wealth_fraction']),
           100*p['investment_share'],p['inflation_target'],p['policy_base'],p['profit_share'],0.,
           p['weekly_hours'],p['household_debt'],0.,p['retired_fraction']]
    rows=[];max_stock_flow_error=0.
    for i in range(n+1):
        t=i*dt;q=effective(p,shocks,t)
        P,K,J,L,A,B,Q,N,Dw,Do,I,pe,rate,theta,S,h,H,knowledge,retired=state
        if min(P,K,L,A,Dw,Do,h,H,knowledge)<0 or J<0 or B<-1e-8:
            raise ModelError(f'Year {t:g}: a household deposit, physical stock or government debt crosses its model boundary. No clipping was substituted.')
        if P<=0 or K<=0 or L<=0 or h<=0 or pe<=-.9:
            raise ModelError('Invalid price, labour, production or expected-inflation state.')
        labour_effective=L*((1-retired)/(1-DEFAULTS['retired_fraction']))*(q['participation']/DEFAULTS['participation'])*h/DEFAULTS['weekly_hours']
        capacity=100/p['normal_utilisation']*A*((K+q['public_efficiency']*J)/effective_k0)**q['alpha']*(labour_effective/L0)**(1-q['alpha'])
        f=flows(q,state,t,capacity,p)
        if not all(math.isfinite(v) for v in f.values()) or abs(f['inflation'])>1 or f['nominal_gdp']>1e10:
            raise ModelError(f'Year {t:g}: extreme inflation or scale leaves the model domain.')
        rows.append(f)
        if i==n:break
        desired=q['investment_share']*capacity*q['normal_utilisation']*math.exp(-q['interest_sensitivity']*f['rate_gap']+q['accelerator']*(f['utilisation']/q['normal_utilisation']-1))
        target_rate=max(-.01,q['policy_base']+q['policy_inflation_response']*(f['inflation']-q['inflation_target'])+q['policy_gap_response']*(f['utilisation']/q['normal_utilisation']-1))
        deltaB=f['deficit']*dt;deltaQ=(f['investment']-f['firm_saving'])*dt;deltaN=f['net_exports']*dt
        deltaH=f['household_borrowing']*dt
        deltaDw=f['worker_saving']*dt+deltaH;deltaDo=f['owner_saving']*dt
        innovation=q['innovation_efficiency']*q['innovation_success']*knowledge/(K+knowledge)
        state=[P*math.exp(f['inflation']*dt),K+((1-q['innovation_share'])*I-q['depreciation']*K)*dt,
               J+(f['public_investment']/P-q['depreciation']*J)*dt,
               L*math.exp(q['population_growth']*dt),A*math.exp((q['productivity_growth']+innovation)*dt),
               B+deltaB,Q+deltaQ,N+deltaN,Dw+deltaDw,Do+deltaDo,
               relaxation(I,desired,dt,q['investment_delay']),
               relaxation(pe,(1-q['expectation_anchor'])*f['inflation']+q['expectation_anchor']*q['inflation_target'],dt,q['expectation_delay']),
               relaxation(rate,target_rate,dt,q['policy_delay']),relaxation(theta,q['profit_share'],dt,q['wage_delay']),
               relaxation(S,q['sentiment_target'],dt,q['sentiment_delay']),
               relaxation(h,f['desired_hours'],dt,q['hours_adjustment']),H+deltaH,
               knowledge+(q['innovation_share']*I-q['depreciation']*knowledge)*dt,
               retired+q['ageing_trend']*dt]
        max_stock_flow_error=max(max_stock_flow_error,abs(deltaB+deltaQ+deltaN+deltaH-deltaDw-deltaDo))
    val,error=valuation(rows,p,shocks)
    if val:
        for f,v in zip(rows,val.pop('values')):
            f.update(equity_value=v,pe=v/f['earnings'] if f['earnings']>0 else None,
                     market_cap_gdp=v/f['nominal_gdp'],equity_real=v/f['price'])
    else:
        for f in rows:f.update(equity_value=None,pe=None,market_cap_gdp=None,equity_real=None)
    for f in rows:
        v=f['equity_value']
        f['worker_total_wealth']=None if v is None else f['worker_net_liquid_wealth']+p['worker_equity_fraction']*v+f['worker_land_value']
        f['owner_total_wealth']=None if v is None else f['owner_deposits']+(1-p['worker_equity_fraction']-p['public_equity_fraction'])*v+f['owner_land_value']
    warnings=[]
    if max(x['utilisation'] for x in rows)>1.1:warnings.append('Utilisation exceeds 110%: the soft capacity benchmark is outside its preferred range.')
    if min(x['utilisation'] for x in rows)<.65:warnings.append('Utilisation falls below 65%: default and labour-market destruction are not modelled.')
    if max(abs(x['inflation']) for x in rows)>.15:warnings.append('Inflation exceeds 15% in magnitude; price and expectations responses are unvalidated in this range.')
    if max(x['essential_shortfall'] for x in rows)>.1:warnings.append('Some wage-household essential needs remain unmet; desired hours are not a guarantee of jobs or adequate income.')
    if any(x['required_hours']>q['maximum_hours'] for x in rows):warnings.append('Required hours exceed the work-time ceiling in at least one period.')
    if val and val['terminal_share']>.7:warnings.append('More than 70% of equity value is terminal. Inspect the sensitivity to growth and required returns.')
    if p['reserve_backing']>0:warnings.append('Reserve backing uses matched, accommodating Treasury credit. This is not a replication of Fisher or the Benes–Kumhof DSGE; compare their separate transition ledgers.')
    if error:warnings.append(error)
    diagnostics={k:max(abs(f[k]) for f in rows) for k in ('goods_residual','sector_residual','bank_residual')}
    diagnostics['stock_flow_residual']=max_stock_flow_error
    diagnostics['accounting_pass']=max(diagnostics.values())<1e-7
    return dict(parameters=p,shocks=shocks,rows=rows,valuation=val,valuation_error=error,
                diagnostics=diagnostics,warnings=warnings,version=VERSION)


def transaction_matrix(f):
    w,o,fc,fk,b,g,x=range(7);result=[]
    def add(label,values):
        row=[0.]*7
        for i,v in values.items():row[i]=v
        result.append(dict(label=label,values=row))
    add('Workers consumption',{w:-f['cw'],fc:f['cw']})
    add('Owners consumption',{o:-f['co'],fc:f['co']})
    add('Private investment',{fc:f['investment'],fk:-f['investment']})
    add('Government purchases',{fc:f['government'],g:-f['government']})
    add('Net exports',{fc:f['net_exports'],x:-f['net_exports']})
    add('Wages',{fc:-f['wages'],w:f['wages']})
    for label,amount,dest in [('Workers land rents',f['rent_w'],w),('Owners land rents',f['rent_o'],o),('Public land rents',f['rent_public'],g),('Tax on private land rent',f['tax_land'],g)]:add(label,{fc:-amount,dest:amount})
    add('Wage tax',{w:-f['tax_w'],g:f['tax_w']})
    add('Corporate tax',{fc:-f['tax_f'],g:f['tax_f']})
    add('Owner stabilising tax',{o:-f['tax_o'],g:f['tax_o']})
    add('Worker wealth tax',{w:-f['wealth_tax_w'],g:f['wealth_tax_w']})
    add('Owner wealth tax',{o:-f['wealth_tax_o'],g:f['wealth_tax_o']})
    add('Transfers to workers',{g:-f['transfer_w'],w:f['transfer_w']})
    add('Transfers to owners',{g:-f['transfer_o'],o:f['transfer_o']})
    add('Business net interest',{fc:-f['firm_interest'],b:f['firm_interest']})
    add('Household loan interest',{w:-f['household_interest'],b:f['household_interest']})
    add('Government bill interest',{g:-f['government_interest'],b:f['government_interest']})
    add('Reserve interest',{g:-f['reserve_interest'],b:f['reserve_interest']})
    add('Treasury funding interest',{b:-f['treasury_interest'],g:f['treasury_interest']})
    add('Bank distribution to workers',{b:-f['bank_w'],w:f['bank_w']})
    add('Bank distribution to owners',{b:-f['bank_o'],o:f['bank_o']})
    for label,amount,dest in [('Worker corporate dividends',f['div_w'],w),('Owner corporate dividends',f['div_o'],o),('Public corporate dividends',f['div_g'],g)]:add(label,{fc:-amount,dest:amount})
    add('Retained gross saving',{fc:-f['firm_saving'],fk:f['firm_saving']})
    dq=f['investment']-f['firm_saving'];dh=f['household_borrowing']
    add('Change in business net debt',{fk:dq,b:-dq})
    add('Change in household loans',{w:dh,b:-dh})
    add('Change in government bills',{g:f['deficit'],b:-f['deficit']})
    add('Change in workers deposits',{w:-(f['worker_saving']+dh),b:f['worker_saving']+dh})
    add('Change in owners deposits',{o:-f['owner_saving'],b:f['owner_saving']})
    add('Change in external settlement asset',{b:-f['net_exports'],x:f['net_exports']})
    deposit_flow=f['worker_saving']+f['owner_saving']+dh
    funding_flow=f['reserve_backing']*deposit_flow
    add('Change in reserve backing',{b:-funding_flow,g:funding_flow})
    add('Change in Treasury credit',{b:funding_flow,g:-funding_flow})
    return dict(columns=['Wage households','Asset households','Business current','Business capital','Bank','Government','Foreign'],rows=result,
                column_sums=[sum(r['values'][i] for r in result) for i in range(7)],max_row_error=max(abs(sum(r['values'])) for r in result))


def bond_price(yield_rate, coupon=.04, years=10):
    if yield_rate <= -1 or years<1:
        raise ModelError('Bond yield must exceed -100% and maturity must be positive.')
    return sum(100*coupon/(1+yield_rate)**i for i in range(1,years+1))+100/(1+yield_rate)**years


def compare(config=None, shocks=None):
    base=simulate(config,[])
    scenario=simulate(config,shocks)
    sensitivity=[]
    for rg in (-.01,0,.01):
        line=[]
        for rd in (-.01,0,.01):
            value,reason=valuation(scenario['rows'],scenario['parameters'],scenario['shocks'],rd,rg)
            line.append(dict(value=value['value'] if value else None,reason=reason,rate_shift=rd,growth_shift=rg))
        sensitivity.append(line)
    y0=base['rows'][0]['risk_free_yield']
    coupon=y0
    bonds=[dict(yield_shift=d,price=bond_price(y0+d,coupon)) for d in (-.02,-.01,0,.01,.02)]
    return dict(baseline=base,scenario=scenario,sensitivity=sensitivity,bonds=bonds,
                bond_assumptions=dict(initial_yield=y0,coupon=coupon,years=10,par=100),version=VERSION)
