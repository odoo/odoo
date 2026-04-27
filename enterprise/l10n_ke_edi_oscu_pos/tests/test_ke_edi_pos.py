from unittest.mock import patch
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged
from odoo.fields import Command


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericKE(TestGenericLocalization):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ke')
    def setUpClass(cls):
        super().setUpClass()

        cls.whiteboard_pen.write({
            'l10n_ke_product_type_code': '2',
            'l10n_ke_packaging_unit_id': cls.env['l10n_ke_edi_oscu.code'].search([('code', '=', 'BA')], limit=1).id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '52161557'),
            ], limit=1).id,
            'l10n_ke_origin_country_id': cls.env.ref('base.be').id,
            'l10n_ke_packaging_quantity': 2,
            'standard_price': 10.0,
            'taxes_id': [Command.link(cls.tax_sale_a.id)]
        })

        cls.wall_shelf.write({
            'l10n_ke_product_type_code': '2',
            'l10n_ke_packaging_unit_id': cls.env['l10n_ke_edi_oscu.code'].search([('code', '=', 'BA')], limit=1).id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '52161557'),
            ], limit=1).id,
            'l10n_ke_origin_country_id': cls.env.ref('base.be').id,
            'l10n_ke_packaging_quantity': 2,
            'standard_price': 10.0,
            'taxes_id': [Command.link(cls.tax_sale_a.id)]
        })

    @patch('odoo.addons.l10n_ke_edi_oscu_pos.models.pos_order.PosOrder.post_order_to_etims', return_value={})
    def test_generic_localization(self, mock_post_order_to_etims):
        super().test_generic_localization()
