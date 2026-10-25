import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import model, finance, archetypes, laboratory

class ExtensionAccounts(unittest.TestCase):
    def run_case(self,**kw):return model.simulate(dict(years=5,**kw))
    def test_full_institutional_matrix_and_debt_creation(self):
        r=self.run_case(household_debt=40,household_credit_growth=.03,reserve_backing=1,cancel_public_bonds=1,land_rent_share=.06,land_tax=.5,worker_land_fraction=.2,public_land_fraction=.3,worker_equity_fraction=.2,public_equity_fraction=.1,worker_bank_fraction=.2,pension_share=.02,wealth_tax=.01,innovation_share=.15)
        for a,b in zip(r['rows'],r['rows'][1:]):
            m=model.transaction_matrix(a)
            self.assertLess(max(abs(x) for x in m['column_sums']),1e-8)
            self.assertLess(m['max_row_error'],1e-8)
            dt=b['t']-a['t']
            self.assertAlmostEqual(b['worker_deposits']-a['worker_deposits'],(a['worker_saving']+a['household_borrowing'])*dt,8)
            self.assertAlmostEqual(b['household_debt']-a['household_debt'],a['household_borrowing']*dt,8)
            self.assertAlmostEqual(a['reserves'],a['deposits'],8)
            self.assertAlmostEqual(a['treasury_funding'],a['reserves']-80,8)
    def test_investment_is_counted_once_across_capital_types(self):
        rows=self.run_case(innovation_share=.25)['rows']
        for a,b in zip(rows,rows[1:]):
            dt=b['t']-a['t'];change=b['private_capital']+b['knowledge_capital']-a['private_capital']-a['knowledge_capital']
            self.assertAlmostEqual(change,(a['investment']-a['depreciation'])/a['price']*dt,8)
    def test_land_distribution_respects_total_ownership(self):
        f=self.run_case(land_rent_share=.06,worker_land_fraction=.2,public_land_fraction=.3,land_tax=.5)['rows'][0]
        self.assertAlmostEqual(f['rent_w'],f['rent']*.2*.5,9)
        self.assertAlmostEqual(f['rent_o'],f['rent']*.5*.5,9)
        self.assertAlmostEqual(f['rent_public']+f['rent_w']+f['rent_o']+f['tax_land'],f['rent'],9)
    def test_public_equity_dividends_have_fiscal_counterpart(self):
        a=self.run_case()['rows'][0];b=self.run_case(public_equity_fraction=.2)['rows'][0]
        self.assertGreater(b['div_g'],0)
        self.assertAlmostEqual(b['div_g']+b['div_w']+b['div_o'],b['dividend'],9)
        self.assertLess(b['deficit'],a['deficit'])
    def test_reserve_reclassification_does_not_erase_broad_public_liability(self):
        a=self.run_case()['rows'][0];b=self.run_case(reserve_backing=1,cancel_public_bonds=1)['rows'][0]
        self.assertEqual(b['government_debt'],0)
        self.assertEqual(b['deposits'],a['deposits'])
        self.assertAlmostEqual(b['government_debt']+b['reserves']-b['treasury_funding'],80)
    def test_transition_plan_financial_net_worth_sums_zero(self):
        for net in (-30,0,20):
            r=self.run_case(household_debt=40,net_foreign_assets=net)
            p=finance.monetary_plans(r,{'plan_private_relief':.8})
            for k in ('fisher','kumhof'):
                self.assertAlmostEqual(sum(x['net_worth'] for x in p[k]['rows']),0,9)
                for x in p[k]['rows']:self.assertAlmostEqual(x['assets']-x['liabilities'],x['net_worth'],9)
            self.assertEqual(p['kumhof']['public_net_worth_change'],-p['kumhof']['private_debt_relief'])
    def test_ageing_changes_workforce_and_obligations(self):
        a=self.run_case(pension_share=.02)['rows'][-1];b=self.run_case(pension_share=.02,ageing_trend=.006)['rows'][-1]
        self.assertGreater(b['retired_fraction'],a['retired_fraction']);self.assertLess(b['workforce'],a['workforce']);self.assertGreater(b['old_age_dependency'],a['old_age_dependency'])
    def test_income_and_substitution_preferences_can_reverse_hours(self):
        a=self.run_case(productivity_growth=.03,hours_income_effect=.6,hours_substitution_effect=.1)['rows'][-1]
        b=self.run_case(productivity_growth=.03,hours_income_effect=.1,hours_substitution_effect=.6)['rows'][-1]
        self.assertLess(a['weekly_hours'],b['weekly_hours'])
    def test_household_debt_service_raises_budget_required_hours(self):
        a=self.run_case(household_debt=40,essential_consumption_share=.5)['rows'][0]
        b=self.run_case(household_debt=40,household_credit_spread=.1,essential_consumption_share=.5)['rows'][0]
        self.assertGreater(b['required_hours'],a['required_hours'])
    def test_smaller_opening_hours_reduce_capacity(self):
        a=self.run_case()['rows'][0];b=self.run_case(weekly_hours=30)['rows'][0]
        self.assertLess(b['capacity'],a['capacity'])
        self.assertLess(b['effective_labour'],a['effective_labour'])
        self.assertGreater(b['net_hourly_wage_index'],a['net_hourly_wage_index'])
    def test_wage_index_does_not_hide_tax_changes_by_rebasing(self):
        a=self.run_case()['rows'][0];b=self.run_case(wage_tax=.1)['rows'][0]
        self.assertGreater(b['net_hourly_wage_index'],a['net_hourly_wage_index'])

class FinanceTests(unittest.TestCase):
    def test_matched_ratios_and_cash_flows(self):
        r=model.simulate({'years':5,'land_rent_share':.05,'household_debt':30});a=finance.aggregate(r)
        self.assertLess(a['max_fcfe_residual'],1e-8);self.assertLess(a['max_financing_residual'],1e-8);self.assertLess(a['max_operating_residual'],1e-8)
        for x in a['rows']:
            if x['ps_residual'] is not None:self.assertAlmostEqual(x['ps_residual'],0,9)
            if x['ev_sales_residual'] is not None:self.assertAlmostEqual(x['ev_sales_residual'],0,9)
    def test_turnover_changes_ps_not_gdp_or_pe(self):
        r=model.simulate({'years':3});a=finance.aggregate(r,2)['rows'][0];b=finance.aggregate(r,4)['rows'][0]
        self.assertEqual(a['pe'],b['pe']);self.assertAlmostEqual(a['ps'],2*b['ps'])
    def test_unknown_claim_does_not_become_zero(self):
        r=model.simulate({'years':3});x=finance.issuer(r,{'preferred':None})
        self.assertIsNone(x['rows'][0]['fair_equity']);self.assertIsNone(x['rows'][0]['observed_ev_sales']);self.assertIn('preferred',x['claims']['missing'])
    def test_fx_is_required_and_applied_once(self):
        r=model.simulate({'years':3});a=finance.issuer(r,{'currency':'USD','quote_currency':'GBP'})
        self.assertIsNone(a['rows'][0]['observed_pe'])
        b=finance.issuer(r,{'currency':'USD','quote_currency':'GBP','quote_to_reporting':2});c=finance.issuer(r,{'currency':'USD','quote_currency':'USD'})
        self.assertAlmostEqual(b['rows'][0]['observed_pe'],2*c['rows'][0]['observed_pe'])
    def test_mismatched_lease_scope_is_withheld(self):
        x=finance.issuer(model.simulate({'years':3}),{'leases':30})
        self.assertIsNone(x['rows'][0]['fair_equity']);self.assertIsNone(x['rows'][0]['observed_ev_ebitda']);self.assertIn('matched lease',x['reason'])
    def test_terminal_failure_is_explicit(self):
        r=model.simulate({'years':3})
        for p in ({'terminal_discount':.02,'terminal_growth':.03},{'terminal_roic':.02,'terminal_growth':.03},{'labour_cost_share':.9,'input_cost_share':.9}):
            x=finance.issuer(r,p);self.assertIsNone(x['rows'][0]['fair_equity']);self.assertTrue(x['reason'])
    def test_rate_increase_reduces_value_on_same_operations(self):
        r=model.simulate({'years':3});a=finance.issuer(r);b=finance.issuer(r,{'discount_rate':.12,'terminal_discount':.12})
        self.assertLess(b['rows'][0]['fair_equity'],a['rows'][0]['fair_equity'])
    def test_wheat_cost_and_nominal_scaling_are_distinct(self):
        x=finance.thought_experiments(model.simulate({'years':1}),finance.validate({'wheat_labour_share':.3,'wheat_productivity_multiple':10,'wheat_nominal_scale':10}))['wheat']
        self.assertAlmostEqual(x['relative_price'],.73);self.assertAlmostEqual(x['nominal_price'],7.3)
    def test_finite_strict_issuer_validation(self):
        for p in ({'bad':1},{'debt':True},{'sales':float('nan')},{'source':12},{'terminal_roic':None}):
            with self.assertRaises(ValueError):finance.validate(p)
    def test_insolvent_residual_is_not_a_negative_equity_price(self):
        x=finance.issuer(model.simulate({'years':3}),{'debt':100000})
        self.assertIsNone(x['rows'][0]['fair_price'])
        self.assertTrue(any('limited-liability' in w for w in x['warnings']))

class ArchetypeTests(unittest.TestCase):
    def test_meta_endpoints_are_inside_the_default_demonstration_domain(self):
        for name,m in archetypes.META.items():
            for end in ('low_values','high_values'):
                for shocks in ([],archetypes.experiment('fiscal')):
                    self.assertTrue(model.simulate(m[end],shocks)['diagnostics']['accounting_pass'],(name,end,shocks))
    def test_all_bundles_and_experiments_qualified_at_default_horizon(self):
        for a in archetypes.ARCHETYPES:
            for shocks in ([],archetypes.experiment('fiscal')):
                r=model.simulate(archetypes.blend({},a['id'],1)['parameters'],shocks);self.assertTrue(r['diagnostics']['accounting_pass'],a['id'])
        for name,_ in archetypes.EXPERIMENTS:self.assertTrue(model.simulate({},archetypes.experiment(name))['diagnostics']['accounting_pass'],name)
    def test_interpolation_has_correct_endpoints_and_leaves_base_untouched(self):
        b=model.validate({});old=dict(b);a=archetypes.blend(b,'kumhof',0)['parameters'];self.assertEqual(a,b)
        a=archetypes.blend(b,'kumhof',.5)['parameters'];self.assertEqual(a['reserve_backing'],.5);self.assertEqual(b,old)
        for t in (-1,2,True,float('nan')):
            with self.assertRaises(ValueError):archetypes.blend({},'fisher',t)
    def test_shared_grid_and_actual_sensitivity(self):
        for bad in ([],False,'',0):
            with self.assertRaises(ValueError):laboratory.analyse(bad,[])
            with self.assertRaises(ValueError):laboratory.analyse({},[],scenario_parameters=bad)
        with self.assertRaises(ValueError):laboratory.analyse({'years':2},[],scenario_parameters={'years':3})
        x=laboratory.analyse({'years':3},[dict(parameter='policy_base',amount=.02,start=1,end=2,shape='step')])
        self.assertAlmostEqual(x['sensitivity'][1][1]['value'],x['scenario']['valuation']['value'])
        self.assertEqual(len(x['scenario']['account_values']),len(x['scenario']['rows']))

if __name__=='__main__':unittest.main()
