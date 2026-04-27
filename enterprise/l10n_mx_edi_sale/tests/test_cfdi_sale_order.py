from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDISaleOrder(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['product.pricelist'].search([]).unlink()
        cls.env.user.groups_id |= cls.env.ref('sales_team.group_sale_salesman')

    def test_sale_order_auto_cfdi_to_public(self):
        """ Test that the field l10n_mx_edi_cfdi_to_public on sale orders is correctly computed
        depending on the non completeness of the partner address (zip or country missing)
        """
        partner_without_zip = self.partner_mx.copy({'zip': False})
        partner_without_country = self.partner_mx.copy({'country_id': False})
        sale_orders = self.env['sale.order'].create([{
            'partner_id': partner.id,
        } for partner in [self.partner_mx, partner_without_zip, partner_without_country]])

        for (order, cfdi_to_public) in zip(sale_orders, [False, True, True]):
            self.assertEqual(order.l10n_mx_edi_partner_address_complete, not cfdi_to_public)
            self.assertEqual(order.l10n_mx_edi_cfdi_to_public, cfdi_to_public)
