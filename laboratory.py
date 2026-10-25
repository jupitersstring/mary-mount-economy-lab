# Copyright (c) 2026 the repository owner. All rights reserved. See LICENSE.
"""One analysed result for the UI, command-line exports and verification."""
import model
import finance
import archetypes


def analyse(parameters=None,shocks=None,issuer_settings=None,scenario_parameters=None):
    reference=model.validate({} if parameters is None else parameters)
    alternative=model.validate(reference if scenario_parameters is None else scenario_parameters)
    if any(reference[k]!=alternative[k] for k in ('years','dt')):
        raise model.ModelError('Reference and alternative must use the same horizon and time step.')
    result=model.compare(reference,[])
    result['scenario']=model.simulate(alternative,shocks)
    result['sensitivity']=[]
    p=result['scenario']['parameters'];rows=result['scenario']['rows'];ss=result['scenario']['shocks']
    for rg in (-.01,0,.01):
        line=[]
        for rd in (-.01,0,.01):
            value,reason=model.valuation(rows,p,ss,rd,rg)
            line.append(dict(value=value['value'] if value else None,reason=reason,rate_shift=rd,growth_shift=rg))
        result['sensitivity'].append(line)
    p=finance.validate(issuer_settings)
    for key in ['baseline','scenario']:
        run=result[key]
        matrices=[model.transaction_matrix(f) for f in run['rows']]
        run['account_layout']=dict(columns=matrices[0]['columns'],labels=[r['label'] for r in matrices[0]['rows']])
        run['account_values']=[[r['values'] for r in m['rows']] for m in matrices]
        run['aggregate_finance']=finance.aggregate(run,p['revenue_to_value_added'])
        run['issuer']=finance.issuer(run,p)
    result['thought_experiments']=finance.thought_experiments(result['scenario'],p)
    result['monetary_plans']=finance.monetary_plans(result['scenario'],p)
    result['issuer_settings']=p
    result['version']=model.VERSION
    return result


def catalogue():
    return dict(archetypes=archetypes.ARCHETYPES,meta=archetypes.META,
                experiments=[dict(id=k,name=v) for k,v in archetypes.EXPERIMENTS],issuer_schema=finance.SCHEMA,issuer_defaults=finance.validate())
