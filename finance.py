# Copyright (c) 2026 the repository owner. All rights reserved. See LICENSE.
"""Operating cash flows, financing claims and matched valuation denominators.
The default issuer is illustrative. National GDP is never called issuer sales.
"""
import math

FIELDS={
 'sales':(1000,1,1e9,'amount','Opening annual sales'),
 'observed_equity':(1500,0,1e10,'amount','Observed / assumed equity value'),
 'debt':(200,0,1e10,'claim','Debt excluding the separately listed lease claim'),
 'cash':(50,0,1e10,'claim','Excess cash available to common equity'),
 'preferred':(0,0,1e10,'claim','Preferred capital'),
 'nci':(0,0,1e10,'claim','Non-controlling interests'),
 'pensions':(0,0,1e10,'claim','Debt-like pension deficit'),
 'leases':(0,0,1e10,'claim','Lease claim; requires a matched operating basis'),
 'nonoperating_assets':(0,0,1e10,'claim','Other separable non-operating assets'),
 'shares':(100,1e-8,1e9,'amount','Diluted shares'),
 'quote_to_reporting':(1,1e-10,1e6,'fx','Reporting-currency units per quote-currency unit'),
 'domestic_share':(.8,0,1,'fraction','Domestic share of sales'),
 'demand_beta':(1,0,3,'coefficient','Volume sensitivity to domestic real GDP'),
 'foreign_growth':(.02,-.1,.15,'rate','Foreign real sales growth'),
 'price_pass':(1,0,2,'coefficient','Pass-through of the domestic price level'),
 'labour_cost_share':(.3,0,.9,'fraction','Opening labour cost / sales'),
 'input_cost_share':(.4,0,.9,'fraction','Opening intermediate input cost / sales'),
 'rent_cost_share':(.03,0,.4,'fraction','Opening cash rent / sales'),
 'productivity_pass':(.5,0,1,'fraction','Productivity gain retained in labour efficiency'),
 'depreciation_share':(.04,0,.4,'fraction','Depreciation / sales'),
 'capex_share':(.06,0,.5,'fraction','Capital investment / sales'),
 'working_capital_share':(.12,0,1,'fraction','Operating working capital / sales'),
 'tax_rate':(.2,0,.6,'fraction','Corporate cash tax assumption'),
 'debt_rate':(.05,0,.3,'rate','Opening borrowing rate'),
 'floating_debt_share':(.5,0,1,'fraction','Share of debt repricing with the policy path'),
 'cash_yield':(.02,0,.2,'rate','Return on excess cash'),
 'discount_rate':(.085,.005,.4,'rate','Operating cash-flow discount rate'),
 'rate_beta':(1,0,2,'coefficient','Operating discount-rate sensitivity to risk-free rates'),
 'erp_beta':(1,0,2,'coefficient','Sensitivity to the equity risk-premium path'),
 'terminal_discount':(.085,.005,.4,'rate','Normalised terminal operating discount rate'),
 'terminal_growth':(.03,-.02,.1,'rate','Terminal nominal operating growth'),
 'terminal_roic':(.14,.005,.5,'rate','Terminal return on incremental operating capital'),
 'revenue_to_value_added':(2,1,10,'coefficient','Model aggregate sales / corporate value added'),
 'fx_debt_fraction':(0,0,1,'fraction','Foreign-currency share of public debt in the separate FX stress'),
 'fx_depreciation':(.2,-.5,2,'fraction','Domestic-currency depreciation in the separate FX stress'),
 'wheat_labour_share':(.3,0,1,'fraction','Labour share of illustrative wheat unit cost'),
 'wheat_productivity_multiple':(10,1,30,'coefficient','Wheat harvesting productivity multiplier'),
 'wheat_input_cost_multiple':(1,0.1,20,'coefficient','Other real wheat input-cost multiplier'),
 'wheat_nominal_scale':(10,.1,100,'coefficient','Common nominal wage and price scaling factor'),
 'plan_liquidity_fraction':(.5,.05,.95,'fraction','Transaction-money share in the Fisher transition illustration'),
 'plan_private_relief':(.5,0,1,'fraction','Private-debt relief fraction in the Kumhof transition illustration'),
}
DEFAULTS={k:v[0] for k,v in FIELDS.items()}
SCHEMA={k:dict(default=v[0],minimum=v[1],maximum=v[2],unit=v[3],label=v[4]) for k,v in FIELDS.items()}
CLAIMS=['debt','preferred','nci','pensions','leases','cash','nonoperating_assets']


def validate(settings=None):
    if settings is not None and not isinstance(settings,dict):raise ValueError('Issuer settings must be an object.')
    unknown=set(settings or {})-set(DEFAULTS)-{'name','currency','quote_currency','source','as_of'}
    if unknown:raise ValueError('Unknown issuer settings: '+', '.join(sorted(unknown)))
    p=dict(DEFAULTS,**(settings or {}))
    for k,(v,low,high,unit,label) in FIELDS.items():
        x=p[k]
        if x is None and (unit=='claim' or k in ('observed_equity','quote_to_reporting')):continue
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not low<=x<=high:
            raise ValueError(label+f' must be between {low} and {high}. Unknown claims may be null.')
    for k in ['name','currency','quote_currency','source','as_of']:
        if k in p and (not isinstance(p[k],str) or len(p[k])>180):raise ValueError('Invalid issuer metadata.')
    p.setdefault('name','Illustrative operating company')
    p.setdefault('currency','MODEL')
    p.setdefault('quote_currency',p['currency'])
    if p['currency']!=p['quote_currency'] and 'quote_to_reporting' not in (settings or {}):p['quote_to_reporting']=None
    p.setdefault('source','Illustrative inputs; no observed issuer or market quote')
    p.setdefault('as_of','Illustrative')
    return p


def ratio(a,b):
    return a/b if a is not None and b is not None and a>0 and b>0 else None


def claims_bridge(equity,p):
    missing=[k for k in CLAIMS if p[k] is None]
    claims=None if missing else p['debt']+p['preferred']+p['nci']+p['pensions']+p['leases']-p['cash']-p['nonoperating_assets']
    ev=None if claims is None or equity is None else equity+claims
    return dict(net_claims=claims,enterprise_value=ev,missing=missing,
                components=[dict(key=k,value=p[k],sign=-1 if k in ('cash','nonoperating_assets') else 1) for k in CLAIMS])


def aggregate(run,turnover=2):
    p=run['parameters'];out=[]
    for f in run['rows']:
        sales=turnover*(f['nominal_gdp']-f['rent'])
        intermediate=sales-(f['nominal_gdp']-f['rent'])
        ebitda=f['gross_surplus'];ebit=ebitda-f['depreciation']
        equity=f['equity_value'];ev=None if equity is None else equity+f['firm_net_debt']
        borrowing=f['investment']-f['firm_saving']
        fcfe=f['earnings']+f['depreciation']-f['investment']+borrowing
        operating_tax=p['corporate_tax']*max(0,ebit)
        fcff=ebit-operating_tax+f['depreciation']-f['investment']
        tax_shield=operating_tax-f['tax_f']
        pe=ratio(equity,f['earnings']);ps=ratio(equity,sales);evsales=ratio(ev,sales);evebitda=ratio(ev,ebitda)
        margin=f['earnings']/sales;ebitda_margin=ebitda/sales
        out.append(dict(t=f['t'],sales=sales,intermediate_inputs=intermediate,wages=f['wages'],ebitda=ebitda,
                        depreciation=f['depreciation'],ebit=ebit,interest=f['firm_interest'],tax=f['tax_f'],
                        net_income=f['earnings'],equity=equity,ev=ev,net_debt=f['firm_net_debt'],
                        pe=pe,ps=ps,ev_sales=evsales,ev_ebitda=evebitda,ev_ebit=ratio(ev,ebit),
                        net_margin=margin,ebitda_margin=ebitda_margin,fcfe=fcfe,fcff=fcff,
                        net_borrowing=borrowing,dividends=f['dividend'],tax_shield=tax_shield,
                        fcfe_residual=fcfe-f['dividend'],
                        financing_residual=fcff-f['firm_interest']+tax_shield+borrowing-fcfe,
                        ps_residual=None if pe is None or ps is None else ps-pe*margin,
                        ev_sales_residual=None if evsales is None or evebitda is None else evsales-evebitda*ebitda_margin,
                        operating_residual=sales-intermediate-f['wages']-ebitda))
    return dict(rows=out,basis='Model corporate sector; sales inferred from an explicit sales/value-added assumption, not observed issuer revenue.',
                max_fcfe_residual=max(abs(x['fcfe_residual']) for x in out),
                max_financing_residual=max(abs(x['financing_residual']) for x in out),
                max_operating_residual=max(abs(x['operating_residual']) for x in out))


def issuer(run,settings=None):
    p=validate(settings);f0=run['rows'][0];out=[];old_wc=None
    for f in run['rows']:
        t=f['t'];P=f['price']/f0['price'];real=f['real_gdp']/f0['real_gdp']
        volume=p['domestic_share']*real**p['demand_beta']+(1-p['domestic_share'])*math.exp(p['foreign_growth']*t)
        sales=p['sales']*volume*P**p['price_pass']
        wage=((f['wages']/f['price'])/(f['workforce']*f['employment_ratio']*f['weekly_hours']))/((f0['wages']/f0['price'])/(f0['workforce']*f0['employment_ratio']*f0['weekly_hours']))
        labour=p['sales']*p['labour_cost_share']*volume*wage*P/(f['productivity']/f0['productivity'])**p['productivity_pass']
        inputs=p['sales']*p['input_cost_share']*volume*P
        rent=p['sales']*p['rent_cost_share']*P*(f['labour']/f0['labour'])**.5
        ebitda=sales-labour-inputs-rent
        depreciation=p['depreciation_share']*sales;ebit=ebitda-depreciation
        capex=p['capex_share']*sales;wc=p['working_capital_share']*sales
        delta_wc=0 if old_wc is None else (wc-old_wc)/run['parameters']['dt'];old_wc=wc
        operating_tax=p['tax_rate']*max(ebit,0);nopat=ebit-operating_tax
        rate_delta=f['risk_free_yield']-f0['risk_free_yield']
        erp_delta=(f['cost_of_equity']-f['risk_free_yield'])-(f0['cost_of_equity']-f0['risk_free_yield'])
        discount=p['discount_rate']+p['rate_beta']*rate_delta+p['erp_beta']*erp_delta
        interest=None if p['debt'] is None or p['cash'] is None else p['debt']*(p['debt_rate']+p['floating_debt_share']*rate_delta)-p['cash']*p['cash_yield']
        income=None if interest is None else (ebit-interest)-p['tax_rate']*max(ebit-interest,0)
        fcff=nopat+depreciation-capex-delta_wc
        out.append(dict(t=t,sales=sales,labour_cost=labour,input_cost=inputs,rent=rent,ebitda=ebitda,ebit=ebit,
                        depreciation=depreciation,capex=capex,working_capital=wc,delta_wc=delta_wc,nopat=nopat,
                        fcff=fcff,interest=interest,net_income=income,discount_rate=discount,
                        operating_residual=sales-labour-inputs-rent-ebitda))
    reason=None;g=p['terminal_growth'];r=p['terminal_discount'];roe=p['terminal_roic']
    if not 0<=g<roe:reason='Terminal growth must be nonnegative and below terminal ROIC.'
    elif r<=g:reason='Terminal operating discount rate must exceed nominal terminal growth.'
    elif out[-1]['nopat']<=0:reason='Terminal operating profit after tax is non-positive; a recovery or liquidation model is required.'
    elif any(x['discount_rate']<=-1 for x in out):reason='An explicit discount rate is at or below -100%.'
    values=None;terminal_share=None
    if reason is None:
        tv=out[-1]['nopat']*(1+g)*(1-g/roe)/(r-g);values=[0.]*len(out);values[-1]=tv
        value=tv;terminal_pv=tv
        for i in range(len(out)-2,-1,-1):
            discount=(1+out[i]['discount_rate'])**(out[i+1]['t']-out[i]['t'])
            value=(out[i]['fcff']*run['parameters']['dt']+value)/discount;values[i]=value;terminal_pv/=discount
        terminal_share=terminal_pv/values[0] if values[0] else None
    quote_fx=1 if p['currency']==p['quote_currency'] else p['quote_to_reporting']
    converted_equity=None if p['observed_equity'] is None or quote_fx is None else p['observed_equity']*quote_fx
    observed=claims_bridge(converted_equity,p)
    if p['leases'] not in (None,0):
        reason='The forecast expenses cash rent. A nonzero capitalised lease claim requires a separate matched lease forecast; equity and EV multiples are withheld.'
    distressed=False
    for i,row in enumerate(out):
        v=values[i] if values else None
        fair=None if v is None or observed['net_claims'] is None or reason else v-observed['net_claims']
        if fair is not None and fair<0:
            distressed=True
            fair=None
        matched=reason is None and p['leases']==0
        row.update(operating_value=v,fair_equity=fair,fair_price=None if fair is None else fair/p['shares'],
                   fair_pe=ratio(fair,row['net_income']),fair_ps=ratio(fair,row['sales']),
                   observed_pe=ratio(converted_equity,row['net_income']) if matched else None,
                   observed_ps=ratio(converted_equity,row['sales']) if matched else None,
                   observed_ev_ebitda=ratio(observed['enterprise_value'],row['ebitda']) if matched else None,
                   observed_ev_ebit=ratio(observed['enterprise_value'],row['ebit']) if matched else None,
                   observed_ev_sales=ratio(observed['enterprise_value'],row['sales']) if matched else None)
    warnings=[]
    if distressed:warnings.append('Operating value falls short of financing claims in at least one period. Common equity is withheld: distress, restructuring and limited-liability option value need a separate model.')
    if observed['missing']:warnings.append('Unknown claims withhold the equity bridge: '+', '.join(observed['missing']))
    if quote_fx is None:warnings.append('Quote and reporting currencies differ and FX is missing. Reference equity value and EV ratios are withheld.')
    if reason:warnings.append(reason)
    if terminal_share is not None and terminal_share>.7:warnings.append('The issuer valuation is more than 70% terminal value.')
    warnings.append('The operating forecast and its macro exposures are assumptions. No fitted issuer relationship or observed-price prediction is established.')
    return dict(settings=p,rows=out,claims=observed,reason=reason,terminal_share=terminal_share,warnings=warnings)


def thought_experiments(run,settings):
    p=validate(settings);f=run['rows'][-1]
    a=p['wheat_productivity_multiple'];lab=p['wheat_labour_share'];other=p['wheat_input_cost_multiple']
    relative=lab/a+(1-lab)*other
    return dict(wheat=dict(productivity_multiple=a,relative_price=relative,nominal_price=relative*p['wheat_nominal_scale'],
                           nominal_wage_scale=p['wheat_nominal_scale'],work_time_price=relative,
                           basis='Fixed real wage, constant markup, explicit labour and other input shares; partial equilibrium, not a wheat forecast.'),
                fixed_nominal_spending=[dict(output_multiple=x,price_index=100/x,nominal_spending=100) for x in [1,2,5,10,20]],
                currency_stress=dict(foreign_currency_debt_fraction=p['fx_debt_fraction'],depreciation=p['fx_depreciation'],
                                     domestic_debt_multiplier=1+p['fx_debt_fraction']*p['fx_depreciation'],
                                     public_debt_before=f['government_debt'],public_debt_after=f['government_debt']*(1+p['fx_debt_fraction']*p['fx_depreciation']),
                                     basis='Standalone currency translation of an unhedged foreign-currency liability; not fed into the domestic-currency stock-flow path.'))


def monetary_plans(run,settings):
    p=validate(settings);f=run['rows'][0]
    B=run['parameters']['government_debt'];Q=run['parameters']['firm_net_debt'];H=run['parameters']['household_debt'];N=run['parameters']['net_foreign_assets']
    D=B+Q+H+N
    money=p['plan_liquidity_fraction']*D
    # Fisher illustration: payment bank separated from a risky investment fund.
    fisher=[dict(institution='Payment bank',assets=money,liabilities=money,net_worth=0),
            dict(institution='Investment fund',assets=D,liabilities=D,net_worth=0),
            dict(institution='Households',assets=money+(D-money),liabilities=H,net_worth=D-H),
            dict(institution='Public money issuer',assets=money,liabilities=money+B,net_worth=-B),
            dict(institution='Businesses net financial position',assets=0,liabilities=Q,net_worth=-Q),
            dict(institution='Foreign settlement counterpart',assets=0,liabilities=N,net_worth=-N)]
    # Public issuer holds fund units equal to the reserves it issues. No gift.
    offset=min(B,D);treasury=D-offset
    relief=min(treasury,p['plan_private_relief']*(max(Q,0)+H))
    relief_h=min(H,relief);relief_q=relief-relief_h
    after_B=B-offset;after_T=treasury-relief;after_Q=Q-relief_q;after_H=H-relief_h
    kumhof=[dict(institution='Deposit and credit bank',assets=after_B+after_Q+after_H+N+D,liabilities=D+after_T,net_worth=0),
            dict(institution='Households',assets=D,liabilities=after_H,net_worth=D-after_H),
            dict(institution='Public money issuer',assets=after_T,liabilities=D+after_B,net_worth=after_T-D-after_B),
            dict(institution='Businesses net financial position',assets=0,liabilities=after_Q,net_worth=-after_Q),
            dict(institution='Foreign settlement counterpart',assets=0,liabilities=N,net_worth=-N)]
    return dict(before=dict(deposits=D,bills=B,business_net_debt=Q,household_debt=H),
                fisher=dict(rows=fisher,money=money,household_investment_units=D-money,public_fund_units=money,
                            reserve_coverage=1,basis='Original illustrative transition, not Fisher\'s complete loan market. The public issuer acquires fund units; transaction money is fully backed and risky lending has separate fund units.'),
                kumhof=dict(rows=kumhof,reserves=D,treasury_credit=after_T,public_bond_offset=offset,
                            private_debt_relief=relief,household_relief=relief_h,business_relief=relief_q,
                            interest_bearing_public_debt=after_B-after_T,broad_public_net_liability=D+after_B-after_T,
                            reserve_coverage=1,public_net_worth_change=-relief,
                            basis='Original public-credit transition inspired by Benes–Kumhof. Not their calibrated DSGE and not their estimated output gain. Debt relief reduces public net worth in this ledger; public money remains on the broad balance sheet.'))
