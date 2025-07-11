from odoo.tests import common


class TestPurchaseAlternativeCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_uom_id = cls.env.ref('uom.product_uom_unit')
        cls.env.user.group_ids += cls.env.ref('uom.group_uom')

        # Create Product
        cls.product_09 = cls.env['product.product'].create({
            'name': 'Pedal Bin',
            'standard_price': 10.0,
            'list_price': 47.0,
            'type': 'consu',
            'uom_id': cls.product_uom_id.id,
            'default_code': 'E-COM10',
        })
        cls.product_13 = cls.env['product.product'].create({
            'name': 'Corner Desk Black',
            'standard_price': 78.0,
            'list_price': 85.0,
            'type': 'consu',
            'uom_id': cls.product_uom_id.id,
            'default_code': 'FURN_1118',
        })

        cls.res_partner_1 = cls.env['res.partner'].create({
            'name': 'Wood Corner',
        })
