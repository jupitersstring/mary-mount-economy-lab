import copy
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import model
import data_adapter


def shock(parameter,amount,start=2,end=5,shape='pulse'):
    return dict(parameter=parameter,amount=amount,start=start,end=end,shape=shape)


class AccountingTests(unittest.TestCase):
    def test_full_transaction_matrix_independently_closes(self):
        for shocks in ([],[shock('government_share',.03)],[shock('net_export_share',-.02)],
                       [shock('worker_transfer_fraction',-.5)],[shock('credit_spread',.015)]):
            run=model.simulate({'years':8},shocks)
            for f in run['rows']:
                matrix=model.transaction_matrix(f)
                for row in matrix['rows']:self.assertAlmostEqual(sum(row['values']),0,places=8,msg=row['label'])
                for total in matrix['column_sums']:self.assertAlmostEqual(total,0,places=8)
                self.assertAlmostEqual(f['nominal_gdp'],f['cw']+f['co']+f['investment']+f['government']+f['net_exports'],places=8)
                self.assertAlmostEqual(f['worker_saving']+f['owner_saving']+f['firm_net_lending'],f['deficit']+f['net_exports'],places=8)
                self.assertAlmostEqual(f['government_debt']+f['firm_net_debt']+f['net_foreign_assets'],f['deposits'],places=8)

    def test_every_stock_changes_by_its_own_flow(self):
        run=model.simulate({'years':8},[shock('net_export_share',-.02)])
        for a,b in zip(run['rows'],run['rows'][1:]):
            h=b['t']-a['t']
            for stock,flow in [('government_debt','deficit'),('net_foreign_assets','net_exports'),
                               ('worker_deposits','worker_saving'),('owner_deposits','owner_saving')]:
                self.assertAlmostEqual(b[stock]-a[stock],a[flow]*h,places=8)
            self.assertAlmostEqual(b['firm_net_debt']-a['firm_net_debt'],(a['investment']-a['firm_saving'])*h,places=8)
            self.assertAlmostEqual(b['private_capital']-a['private_capital'],(a['investment']/a['price']-.05*a['private_capital'])*h,places=8)
            self.assertAlmostEqual(b['public_capital']-a['public_capital'],(a['public_investment']/a['price']-.05*a['public_capital'])*h,places=8)

    def test_nominal_capital_revaluation_is_not_investment(self):
        rows=model.simulate({'years':3},[shock('government_share',.03,start=.5,end=2)])['rows']
        for a,b in zip(rows,rows[1:]):
            h=b['t']-a['t']
            delta_nom=b['price']*b['private_capital']-a['price']*a['private_capital']
            investment_net=(a['investment']-a['depreciation'])*h
            revaluation=(b['price']-a['price'])*b['private_capital']
            self.assertAlmostEqual(delta_nom,investment_net+revaluation,places=8)

    def test_opening_financial_assets_have_counterparts(self):
        r=model.simulate({'government_debt':90,'firm_net_debt':100,'net_foreign_assets':-20,'worker_wealth_fraction':.4,'years':1})['rows'][0]
        self.assertEqual(r['deposits'],170)
        self.assertEqual(r['worker_deposits'],68)
        self.assertEqual(r['owner_deposits'],102)

    def test_random_moderate_parameter_sets(self):
        rng=random.Random(413)
        for _ in range(30):
            p={'years':4,'worker_mpc':rng.uniform(.8,.95),'owner_mpc':rng.uniform(.35,.65),
               'credit_spread':rng.uniform(0,.03),'net_export_share':rng.uniform(-.03,.03),
               'government_share':rng.uniform(.17,.24),'population_growth':rng.uniform(-.005,.015)}
            r=model.simulate(p)
            self.assertTrue(r['diagnostics']['accounting_pass'])


class MechanismTests(unittest.TestCase):
    def test_realised_history_does_not_anticipate_shocks(self):
        b=model.simulate({'years':8})['rows']
        s=model.simulate({'years':8},[shock('government_share',.02,start=4,end=6)])['rows']
        for x,y in zip(b,s):
            if x['t']>=4:break
            for k in ['real_gdp','price','earnings','government_debt','investment','deposits','policy_rate']:
                self.assertEqual(x[k],y[k],k)

    def test_recipient_invariance_when_consumption_rules_identical(self):
        p={'years':6,'worker_mpc':.8,'owner_mpc':.8,'debt_tax_response':0}
        b=model.simulate(p)['rows'];s=model.simulate(p,[shock('worker_transfer_fraction',-.6)])['rows']
        for x,y in zip(b,s):
            for k in ['real_gdp','price','investment','government_debt','deposits']:
                self.assertAlmostEqual(x[k],y[k],places=8)

    def test_recipient_effect_depends_on_propensities(self):
        p={'years':6};b=model.simulate(p)['rows'];s=model.simulate(p,[shock('worker_transfer_fraction',-.6)])['rows']
        index=round(2/model.DEFAULTS['dt'])
        self.assertEqual(b[index]['transfers'],s[index]['transfers'])
        self.assertEqual(b[index]['government'],s[index]['government'])
        self.assertLess(s[index]['real_gdp'],b[index]['real_gdp'])

    def test_population_accumulates_separately_from_productivity(self):
        r=model.simulate({'years':5,'population_growth':.01,'productivity_growth':.02})['rows'][-1]
        self.assertAlmostEqual(r['labour'],100*math.exp(.05),places=8)
        self.assertAlmostEqual(r['productivity'],math.exp(.1),places=8)

    def test_credit_spread_reduces_near_term_investment(self):
        p={'years':6};b=model.simulate(p)['rows'];s=model.simulate(p,[shock('credit_spread',.03)])['rows']
        index=round(2.5/model.DEFAULTS['dt'])
        self.assertLess(s[index]['investment']/s[index]['price'],b[index]['investment']/b[index]['price'])

    def test_pulse_and_ramp_have_stated_endpoints(self):
        p=model.validate({})
        x=shock('government_share',.02)
        self.assertEqual(model.effective(p,[x],1)['government_share'],.2)
        self.assertEqual(model.effective(p,[x],2)['government_share'],.22)
        self.assertEqual(model.effective(p,[x],5)['government_share'],.2)
        x['shape']='ramp'
        self.assertAlmostEqual(model.effective(p,[x],3.5)['government_share'],.21)
        self.assertAlmostEqual(model.effective(p,[x],6)['government_share'],.22)

    def test_time_step_convergence(self):
        finals=[model.simulate({'dt':h})['rows'][-1] for h in (.125,.0625,.03125)]
        for k in ['real_gdp','price','government_debt','earnings']:
            coarse=abs(finals[0][k]-finals[1][k]);fine=abs(finals[1][k]-finals[2][k])
            self.assertLess(fine,coarse*1.05+1e-8,k)
            self.assertLess(fine/abs(finals[2][k]),.02,k)


class ValuationTests(unittest.TestCase):
    def test_flat_distribution_perpetuity_has_known_value(self):
        rows=[dict(t=t,earnings=10,dividend=10,cost_of_equity=.1) for t in range(11)]
        p=model.validate({'terminal_growth':0,'terminal_roe':.1,'terminal_risk_free':.05,'terminal_equity_premium':.05})
        value,error=model.valuation(rows,p,[])
        self.assertIsNone(error)
        self.assertAlmostEqual(value['value'],100,places=8)

    def test_no_epsilon_fix_for_invalid_terminal_spread(self):
        r=model.simulate({'terminal_growth':.07,'terminal_risk_free':.02,'terminal_equity_premium':.01})
        self.assertIsNone(r['valuation'])
        self.assertIn('exceed',r['valuation_error'])
        self.assertTrue(all(x['equity_value'] is None for x in r['rows']))

    def test_growth_requires_retention_and_positive_terminal_earnings(self):
        p=model.validate({'terminal_growth':.03,'terminal_roe':.12})
        rows=[dict(t=t,earnings=10,dividend=5,cost_of_equity=.1) for t in range(5)]
        v,e=model.valuation(rows,p,[]);self.assertAlmostEqual(v['terminal_payout'],.75)
        p['terminal_roe']=.02;self.assertIsNone(model.valuation(rows,p,[])[0])
        p['terminal_roe']=.12;rows[-1]['earnings']=-1;self.assertIsNone(model.valuation(rows,p,[])[0])

    def test_higher_required_return_lowers_value_on_same_cash_flows(self):
        r=model.simulate();a,_=model.valuation(r['rows'],r['parameters'],[],rate_shift=0)
        b,_=model.valuation(r['rows'],r['parameters'],[],rate_shift=.01)
        self.assertLess(b['value'],a['value'])

    def test_announced_future_shock_can_change_todays_value(self):
        r=model.compare({'years':8},[shock('government_share',.02,start=4,end=6)])
        self.assertEqual(r['baseline']['rows'][0]['real_gdp'],r['scenario']['rows'][0]['real_gdp'])
        self.assertNotEqual(r['baseline']['valuation']['value'],r['scenario']['valuation']['value'])

    def test_bond_par_and_yield_order(self):
        self.assertAlmostEqual(model.bond_price(.04,.04,10),100)
        self.assertLess(model.bond_price(.05,.04,10),100)
        self.assertGreater(model.bond_price(.03,.04,10),100)


class ValidationTests(unittest.TestCase):
    def test_invalid_parameter_inputs(self):
        for p in [[], '', {'bad':1},{'years':float('nan')},{'alpha':True},{'dt':0},{'years':1.1,'dt':.25},
                  {'government_debt':0,'firm_net_debt':-100,'net_foreign_assets':0}]:
            with self.assertRaises(model.ModelError):model.simulate(p)

    def test_overlap_is_validated_jointly(self):
        with self.assertRaises(model.ModelError):model.simulate({},[shock('government_share',.2),shock('government_share',.2)])

    def test_stock_shocks_and_bad_timing_are_rejected(self):
        for x in [shock('government_debt',5),shock('government_share',.1,start=5,end=2),shock('government_share',float('inf')),shock('government_share',.01,start=2.01,end=5)]:
            with self.assertRaises(model.ModelError):model.simulate({},[x])

    def test_step_end_is_actually_ignored(self):
        a=model.simulate({'years':6},[shock('government_share',.01,start=2,end=5,shape='step')])
        b=model.simulate({'years':6},[shock('government_share',.01,start=2,end=100,shape='step')])
        self.assertEqual(a['rows'],b['rows'])

    def test_invalid_valuation_does_not_hide_accounting(self):
        r=model.simulate({'terminal_growth':.08,'terminal_roe':.05})
        self.assertIsNone(r['valuation'])
        self.assertTrue(r['diagnostics']['accounting_pass'])


class DataTests(unittest.TestCase):
    def test_quarterly_import_preserves_saar_ratios(self):
        d=data_adapter.parse_csv('date,GDP,GCE,GPDI,NETEXP\n2025-01-01,100,20,20,-3\n')
        self.assertEqual(d['anchors']['government_share'],.2)
        self.assertEqual(d['anchors']['net_export_share'],-.03)
        self.assertIn('not verified',d['vintage'])

    def test_csv_bom_and_negative_profit_context(self):
        d=data_adapter.parse_csv('\ufeffdate,GDP,GCE,GPDI,NETEXP,CPATAX\n2025-01-01,100,20,20,-3,-1\n')
        self.assertEqual(d['series'][-1]['observations'][0]['value'],-1)
        with self.assertRaises(ValueError):data_adapter.parse_csv('date,GDP,GDP,GCE,GPDI,NETEXP\n2025-01-01,100,100,20,20,-3')

    def test_missing_nonfinite_duplicates_and_wrong_frequency_fail(self):
        for text in ['date,GDP\n2025-01-01,100',
                     'date,GDP,GCE,GPDI,NETEXP\n2025-01-01,nan,20,20,-3',
                     'date,GDP,GCE,GPDI,NETEXP\n2025-02-01,100,20,20,-3',
                     'date,GDP,GCE,GPDI,NETEXP\n2025-01-01,100,20,20,-3\n2025-01-01,100,20,20,-3']:
            with self.assertRaises(ValueError):data_adapter.parse_csv(text)

    def test_anchors_do_not_mix_quarters(self):
        snap={'series':[{'series_id':k,'observations':[{'date':d,'value':v}]} for k,d,v in [
            ('GDP','2025-01-01',100),('GCE','2025-04-01',20),('GPDI','2025-01-01',20),('NETEXP','2025-01-01',-3)]]}
        self.assertEqual(data_adapter.anchors(snap),{})

    def test_period_mapping(self):
        self.assertEqual(data_adapter.period_date('Q2 2026'),'2026-04-01')
        self.assertEqual(data_adapter.period_date('Sep 2026'),'2026-09-01')

    def test_failed_refresh_retains_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'snapshot.json';p.write_text('{"saved":"prior snapshot"}')
            with patch.object(data_adapter,'fetch_series',side_effect=TimeoutError('offline')):
                with self.assertRaises(TimeoutError):data_adapter.refresh(p)
            self.assertEqual(p.read_text(),'{"saved":"prior snapshot"}')

    def test_public_page_parser_checks_values_and_units(self):
        html=b'''Billions of Dollars <td align="right">Q2 2026:&nbsp;</td><td class="series-obs value">32,563.030</td><td>Q1 2026:&nbsp;</td><td class="series-obs value">31,906.274</td>'''
        import io
        with patch.object(data_adapter.urllib.request,'urlopen',return_value=io.BytesIO(html)):
            s=data_adapter.fetch_series('GDP')
        self.assertEqual(s['observations'][0]['value'],32563.03)
        with patch.object(data_adapter.urllib.request,'urlopen',return_value=io.BytesIO(html.replace(b'Billions of Dollars',b'Unknown unit'))):
            with self.assertRaises(ValueError):data_adapter.fetch_series('GDP')


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('launcher',ROOT/'hard_money_forrester_with_knobs.py')
        cls.app=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.app)
        cls.server=cls.app.ThreadingHTTPServer(('127.0.0.1',0),cls.app.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def request(self,path,data=None,headers=None):
        h={'Content-Type':'application/json'};h.update(headers or {})
        req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=h)
        return urllib.request.urlopen(req,timeout=5)

    def test_ui_and_bootstrap(self):
        with self.request('/') as response:self.assertIn(b'MARY MOUNT RESEARCH',response.read())
        with self.request('/api/bootstrap') as response:
            data=json.load(response);self.assertTrue(data['result']['scenario']['diagnostics']['accounting_pass'])
            self.assertIn('monetary_plans',data['result'])
            self.assertIn('issuer',data['result']['scenario'])

    def test_run_and_rejection(self):
        with self.request('/api/run',{'parameters':{'years':2},'shocks':[]}) as response:
            data=json.load(response);self.assertEqual(data['scenario']['rows'][-1]['t'],2)
        with self.assertRaises(urllib.error.HTTPError) as cm:self.request('/api/run',{'parameters':{'dt':0}})
        self.assertEqual(cm.exception.code,400)

    def test_static_json_downloads_are_not_reencoded_as_objects(self):
        with self.request('/issuer-template.json') as response:
            data=json.load(response);self.assertEqual(data['sales'],1000)
        with self.request('/data/fred_snapshot.json') as response:
            data=json.load(response);self.assertEqual(len(data['series']),8)

    def test_routes_and_origin_are_bounded(self):
        for path in ['/model.py','/../model.py','/data/../../model.py']:
            with self.assertRaises(urllib.error.HTTPError) as cm:self.request(path)
            self.assertEqual(cm.exception.code,404)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.request('/api/run',{'parameters':{}},headers={'Origin':'https://example.com'})
        self.assertEqual(cm.exception.code,403)


if __name__=='__main__':unittest.main()
