from odoo.addons.stock.tests.test_old_rules import TestOldRules

class TestStockMtso(TestOldRules):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        #   cls.ProductObj = cls.env['product.product']
        #   cls.UomObj = cls.env['uom.uom']
        #   cls.PartnerObj = cls.env['res.partner']
        #   cls.ModelDataObj = cls.env['ir.model.data']
        #   cls.StockPackObj = cls.env['stock.move.line']
        #   cls.StockQuantObj = cls.env['stock.quant']
        #   cls.PickingObj = cls.env['stock.picking']
        #   cls.MoveObj = cls.env['stock.move']
        #   cls.LotObj = cls.env['stock.lot']
        #   cls.StockLocationObj = cls.env['stock.location']

        # Products: P, M, I, Raw I
        #   cls.productA
        #   cls.productB
        #   cls.productC
        #   cls.productD
        #   cls.productE

        # WH: 1s, 2s, 3s
        cls.warehouse_1_step = cls.warehouse_1
        # cls.warehouse_2_steps  # pull
        # cls.warehouse_3_steps  # pull
        #For purchase :
        # Partner
        # cls.partner_1 = cls.env['res.partner'].create({
        # 'name': 'Julia Agrolait',
        # 'email': 'julia@agrolait.example.com',
        # })

        # Route MTSO: route MTO:>rules.procure_method = mts_else_mto
        route_mto = cls.warehouse_1.mto_pull_id.route_id
        for r in route_mto.rule_ids:
            r.procure_method = 'mts_else_mto'
        cls.route_mtso = route_mto

        # self.env['stock.quant']._update_available_quantity(prod, location, qty, lot_id=...)
