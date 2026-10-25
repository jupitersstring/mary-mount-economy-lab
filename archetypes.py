# Copyright (c) 2026 the repository owner. All rights reserved. See LICENSE.
"""Interpretive bundles, not estimated party positions or historical replicas.
Numbers are lab design choices. Sources describe ideas, not numeric calibrations.
Meta endpoints are moderate demonstration ranges, not ideological maxima.
"""
import math
import model

ARCHETYPES=[
 dict(id='reference',name='Reference mixed credit economy',author='Laboratory reference',
      question='How do the mechanisms interact before changing the institutional assumptions?',values={},
      sources=['https://www.levyinstitute.org/pubs/Lavoie%20Godley_2001-02.pdf'],
      limit='Synthetic reference economy; no country, party or fitted consensus is represented.'),
 dict(id='smith',name='Smith inspired commercial society',author='Adam Smith 1776',
      question='Can competitive commerce and productive finance increase wages and capital together?',
      values=dict(government_share=.16,transfer_share=.035,corporate_tax=.15,profit_share=.31,credit_spread=.008,public_investment_fraction=.2),
      sources=['https://www.econlib.org/library/Smith/smWN.html'],limit='A commercial-policy illustration. Smith did not propose these tax rates and did not advocate unregulated banking.'),
 dict(id='wicksell',name='Wicksell inspired price stability',author='Knut Wicksell 1898 and 1906',
      question='What follows when the lending rate approaches the assumed real investment hurdle?',
      values=dict(policy_base=.03,natural_rate=.02,policy_inflation_response=2,policy_gap_response=.4,expectation_anchor=.9),
      sources=['https://www.econlib.org/library/Essays/wcksInt.html'],limit='Natural interest is assumed, not observed. This is a rate-gap mechanism, not a replication of Wicksell’s pure-credit economy.'),
 dict(id='keynes',name='Keynes inspired stabilisation',author='John Maynard Keynes 1936',
      question='Can public investment and recipient targeting offset weak private demand?',
      values=dict(government_share=.22,transfer_share=.06,wage_tax=.23,corporate_tax=.23,worker_transfer_fraction=.9,public_investment_fraction=.25,debt_tax_response=.08),
      sources=['https://www.files.ethz.ch/isn/125515/1366_KeynesTheoryofEmployment.pdf'],limit='A demand-management bundle. It does not imply that Keynes favoured permanent inflation or one fixed tax programme.'),
 dict(id='mill',name='Mill inspired sufficiency and leisure',author='John Stuart Mill 1848',
      question='Can productivity and broader ownership support fewer paid hours?',
      values=dict(weekly_hours=40,maximum_hours=45,hours_income_effect=.55,hours_substitution_effect=.1,aspiration_growth=0,worker_equity_fraction=.15,wealth_leisure_effect=.25,wage_tax=.23),
      sources=['https://cuny.manifoldapp.org/read/principles-of-political-economy-ashley-ed/section/90895ea2-7781-48f7-b0d0-0f0da398fc4a'],limit='Preferences and ownership are counterfactual opening assignments. The model does not prove leisure is a universal response or reproduce Mill’s stationary state.'),
 dict(id='george',name='Georgist land-rent capture',author='Henry George 1879',
      question='What changes when rents fund government while labour taxes are lower?',
      values=dict(land_rent_share=.06,land_tax=.75,wage_tax=.18,corporate_tax=.2,debt_tax_response=.12,public_investment_fraction=.2),
      sources=['https://www.econlib.org/library/YPDBooks/George/grgPP.html'],limit='A rent-tax experiment with a fixed land-income share. Endogenous land use, construction and location are not modelled.'),
 dict(id='schumpeter',name='Schumpeter inspired innovation credit',author='Joseph Schumpeter 1911 and 1934',
      question='When do present research costs generate enough later productivity to justify credit?',
      values=dict(innovation_share=.2,innovation_success=.5,innovation_efficiency=.25,investment_share=.23,credit_spread=.007),
      sources=['https://cruel.org/books/hy/shortschumpeter/SchumpeterTheoryofEconDev.html'],limit='Expected-value knowledge spillovers, not observed innovation success rates or a reproduction of entrepreneurial cycles.'),
 dict(id='cooperative',name='Broad and public ownership experiment',author='Ownership debate including Marx and Mill',
      question='Can a different ownership allocation change household wealth and fiscal income without changing the accounting identities?',
      values=dict(worker_equity_fraction=.25,public_equity_fraction=.1,worker_land_fraction=.25,worker_bank_fraction=.15,profit_share=.32,wealth_tax=.02,wage_tax=.23,government_share=.18),
      sources=['https://www.marxists.org/archive/marx/works/1867-c1/ch10.htm','https://www.econlib.org/library/Mill/mlP.html'],
      limit='A market economy with alternative opening ownership, not Marx’s theory reproduced or a model of central planning. Reassigning existing ownership is not a free policy cash flow.'),
 dict(id='fisher',name='Fisher 100% Money',author='Irving Fisher 1935',
      question='What changes when payments are fully backed and lending has separate funding?',
      values=dict(reserve_backing=1,cancel_public_bonds=0,inflation_target=.005,expectation_anchor=1,policy_inflation_response=2),
      sources=['https://mises.org/library/book/100-money','https://www.imf.org/external/pubs/ft/wp/2012/wp12202.PDF'],
      limit='Use the Fisher transition ledger for payment-bank/investment-fund separation. The dynamic path uses an accommodating Treasury-funding proxy, not Fisher’s full private savings-funded lending system. Stable money is not fixed-quantity money.'),
 dict(id='kumhof',name='Benes–Kumhof Chicago Plan',author='Jaromir Benes and Michael Kumhof 2012',
      question='How do public reserve issuance, replacement funding and debt offsets change balance sheets?',
      values=dict(reserve_backing=1,cancel_public_bonds=1,inflation_target=.005,expectation_anchor=1,treasury_funding_spread=.005),
      sources=['https://www.imf.org/external/pubs/ft/wp/2012/wp12202.PDF'],
      limit='The transition ledger shows funding and relief counterparts. The core is not their calibrated DSGE and does not import their claimed output gains or debt reductions.'),
 dict(id='rules',name='Rules based monetary discipline',author='Monetarist policy family',
      question='How do anchored nominal expectations interact with a transparent fiscal rule?',
      values=dict(expectation_anchor=1,policy_inflation_response=2.5,debt_tax_response=.1,government_share=.18,wealth_tax=0),
      sources=['https://www.aeaweb.org/aer/top20/58.1.1-17.pdf'],limit='A monetary-rule illustration, not Friedman’s money-growth rule implemented. Bank money remains endogenous.'),
]

META={
 'fiscal':dict(label='Fiscal intensity',low='Smaller transfers and purchases',high='Larger public provision',
               low_values=dict(government_share=.15,transfer_share=.025,wage_tax=.15,corporate_tax=.15),
               high_values=dict(government_share=.25,transfer_share=.08,wage_tax=.27,corporate_tax=.28)),
 'ownership':dict(label='Breadth of ownership',low='Concentrated capital income',high='Broader worker ownership',
                 low_values=dict(worker_equity_fraction=0,worker_bank_fraction=0,worker_land_fraction=0),
                 high_values=dict(worker_equity_fraction=.5,worker_bank_fraction=.2,worker_land_fraction=.5)),
 'leisure':dict(label='Sufficiency orientation',low='Income and status expansion',high='Productivity taken as leisure',
               low_values=dict(hours_income_effect=.1,hours_substitution_effect=.3,aspiration_growth=.01),
               high_values=dict(hours_income_effect=.6,hours_substitution_effect=.1,aspiration_growth=0)),
 'credit':dict(label='Public reserve backing',low='Bank deposit creation',high='Fully backed payments proxy',
               low_values=dict(reserve_backing=0,cancel_public_bonds=0),high_values=dict(reserve_backing=1,cancel_public_bonds=0)),
 'innovation':dict(label='Research investment',low='Physical capital emphasis',high='Knowledge investment with risk',
                   low_values=dict(innovation_share=0),high_values=dict(innovation_share=.25)),
 'rents':dict(label='Capture of land rents',low='Private retention of rent',high='Rent funds public expenditure',
              low_values=dict(land_rent_share=.06,land_tax=0),high_values=dict(land_rent_share=.06,land_tax=.8)),
}


def blend(base,archetype_id,strength):
    if isinstance(strength,bool) or not isinstance(strength,(float,int)) or not math.isfinite(strength) or not 0<=strength<=1:
        raise ValueError('Archetype strength must be between zero and one.')
    chosen=next((a for a in ARCHETYPES if a['id']==archetype_id),None)
    if chosen is None:raise ValueError('Unknown archetype.')
    p=model.validate(base);changes=[]
    for k,target in chosen['values'].items():
        value=p[k]+strength*(target-p[k]);changes.append(dict(parameter=k,before=p[k],after=value));p[k]=value
    model.validate(p)
    return dict(parameters=p,changes=changes,archetype=chosen,strength=strength)


def experiment(name,years=15):
    start=2 if years>5 else 0;end=min(5,years)
    def s(k,a,shape='pulse'):return dict(parameter=k,amount=a,start=start,end=end,shape=shape)
    experiments={
      'none':[], 'fiscal':[s('government_share',.02)],
      'recipients':[s('worker_transfer_fraction',-.6,'step')],
      'rates':[s('policy_base',.02,'step')],
      'deflation':[s('inflation_target',-.03,'step')],
      'productivity':[s('productivity_growth',.005,'step')],
      'population':[s('population_growth',-.005,'step')],
      'credit':[s('credit_spread',.02)],
      'war':[s('government_share',.05),s('public_investment_fraction',-.1)],
      'ageing':[s('ageing_trend',.006,'step'),s('pension_share',.04,'step')],
      'debt_pressure':[s('household_credit_spread',.03,'step')],
      'leisure':[s('hours_income_effect',.35,'step'),s('hours_substitution_effect',-.1,'step')],
      'rent_tax':[s('land_tax',.5,'step'),s('wage_tax',-.04,'step')],
      'research':[s('innovation_share',.2,'step')],
      'failed_research':[s('innovation_share',.2,'step'),s('innovation_success',-.5,'step')],
      'selective_credit':[s('credit_spread',-.005,'step'),s('household_credit_spread',.02,'step')],
      'external_funding':[s('sovereign_spread',.025,'step')],
    }
    if name not in experiments:raise ValueError('Unknown experiment.')
    return experiments[name]

EXPERIMENTS=[('none','No shock'),('fiscal','Temporary fiscal expansion'),('recipients','Same transfers, different recipients'),
 ('rates','Policy rate increase'),('deflation','Lower nominal target with existing debt'),('productivity','Faster productivity'),('population','Slower population growth'),
 ('credit','Credit tightening'),('war','War-type purchases with less public investment'),('ageing','Ageing and pension promises'),
 ('debt_pressure','Household debt-service pressure'),('leisure','Productivity taken as leisure'),('rent_tax','Land tax and lower wage tax'),
 ('research','Research investment'),('failed_research','Research costs without a productivity payoff'),
 ('selective_credit','Preferential business credit'),('external_funding','Higher sovereign funding spread')]
