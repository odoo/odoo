from odoo.addons.stock.tests.test_old_rules import TestOldRules


class TestStockMtso(TestOldRules):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # WH: 1s, 2s, 3s
        cls.warehouse_1s = cls.warehouse_1
        cls.warehouse_2s = cls.warehouse_2_steps
        cls.warehouse_3s = cls.warehouse_3_steps

        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Sopĥia Remblaid',
            'email': 'sophia@remblaid.example.com',
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'Customer',
            'email': 'customer@example.com',
        })

        # N.B. mto_pull_id is common to all warehouses
        cls.route_mtso = cls.warehouse_1s.mto_pull_id.route_id.copy()
        for r in cls.route_mtso.rule_ids:
            r.procure_method = 'mts_else_mto'
