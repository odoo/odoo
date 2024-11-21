from odoo.tests import common, tagged


@tagged('at_install', '-post_install')
class TestGlobalRouteRulesInstallation(common.TransactionCase):
    def test_rule_installation(self):
        company_id = self.env.ref('base.main_company').id
        rule = self.env['stock.rule'].search([
            ('picking_type_id.code', '=', 'repair_operation'),
            ('company_id', '=', company_id)
        ])
        self.assertTrue(rule, "Stock Rule was not created")
        self.assertEqual(rule.procure_method, 'make_to_order', "Procure method is incorrect")
        self.assertEqual(rule.company_id.id, company_id, "Company ID is incorrect")
        self.assertEqual(rule.action, 'pull', "Action is incorrect")
        self.assertEqual(rule.auto, 'manual', "Auto is incorrect")
        self.assertEqual(rule.route_id.name, 'Replenish on Order (MTO)', "Route name is incorrect")
        self.assertEqual(rule.location_dest_id.name, 'Production', "Location dest ID is incorrect")
        self.assertEqual(rule.location_src_id.name, 'Stock', "Location src ID is incorrect")
        self.assertEqual(rule.picking_type_id.name, 'Repairs', "Picking type ID is incorrect")
        self.assertTrue(rule.active, "Rule is not active")
