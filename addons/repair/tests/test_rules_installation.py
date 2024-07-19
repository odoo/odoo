from odoo.tests import common, tagged


@tagged('at_install', '-post_install')
class TestGlobalRouteRulesInstallation(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.ref('base.main_company')

    def test_rule_installation(self):
        rule = self.env['stock.rule'].search([
            ('name', '=', 'WH: Stock → Production (MTO)'),
            ('picking_type_id.name', '=', 'Repairs'),
        ])
        self.assertTrue(rule, "Stock rule was not created")
        self.assertEqual(rule.procure_method, 'mts_else_mto', "Procure method is incorrect")
        self.assertEqual(rule.company_id.id, self.company.id, "Company ID is incorrect")
        self.assertEqual(rule.action, 'pull', "Action is incorrect")
        self.assertEqual(rule.auto, 'manual', "Auto is incorrect")
        self.assertEqual(rule.route_id.name, 'Replenish on Order (MTO)', "Route name is incorrect")
        self.assertEqual(rule.location_dest_id.name, 'Production', "Location dest ID is incorrect")
        self.assertEqual(rule.location_src_id.name, 'Stock', "Location src ID is incorrect")
        self.assertEqual(rule.picking_type_id.name, 'Repairs', "Picking type ID is incorrect")
        self.assertTrue(rule.active, "Rule is not active")
