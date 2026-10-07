from odoo.addons.stock.tests.common import TestStockCommon


class TestL10nTrEdiStockCommon(TestStockCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tr_country_id = cls.env.ref('base.tr').id
        cls.receipt_partner = cls.PartnerObj.with_context(no_vat_validation=True).create({
            'name': 'Test Kurum İki',
            'country_id': cls.tr_country_id,
            'vat': '1234567802',
        })
        cls.driver_partner = cls.PartnerObj.with_context(no_vat_validation=True).create({
            'name': 'Test Driver',
            'country_id': cls.tr_country_id,
            'vat': '11234570890',
        })
        cls.uom_grm = cls.env.ref('uom.product_uom_gram').id
        cls.move_product = cls.ProductObj.create({
            'name': 'Product in GRM',
            'uom_id': cls.uom_grm,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit').id
        cls.uom_kgm = cls.env.ref('uom.product_uom_kgm').id
