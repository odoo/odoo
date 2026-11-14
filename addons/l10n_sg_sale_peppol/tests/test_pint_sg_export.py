from lxml import etree

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPintSgExport(TestSaleCommon):

    @classmethod
    @TestSaleCommon.setup_country('sg')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'vat': '197401143C',
            'l10n_sg_unique_entity_number': '00192200M',
            'street': 'Tyersall Avenue',
            'zip': '248048',
            'city': 'Central Singapore',
            'phone': '+65 9123 4567',
        })
        cls.partner_a.write({
            'vat': 'S16FC0121D',
            'l10n_sg_unique_entity_number': '197401143C',
            'country_id': cls.env.ref('base.sg').id,
            'street': 'that other street, 3',
            'zip': '248050',
            'city': 'East Singapore',
            'phone': '+65 9123 4589',
            'ref': 'CUST-A',
        })
        cls.product_a.invoice_policy = 'order'

    def _get_buyer_reference(self, order_vals):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {'product_id': self.product_a.id, 'product_uom_qty': 1})],
            **order_vals,
        })
        order.action_confirm()
        invoice = order._create_invoices()
        invoice.action_post()

        xml, errors = self.env['account.edi.xml.pint_sg']._export_invoice(invoice)
        self.assertFalse(errors)
        return etree.fromstring(xml).findtext('./{*}BuyerReference')

    def test_buyer_reference_from_peppol_order(self):
        """ The customer reference of an order received over Peppol is returned as BuyerReference. """
        buyer_ref = self._get_buyer_reference({
            'l10n_sg_peppol_order_id': 'PO-0001',
            'client_order_ref': 'DEPT-42',
        })
        self.assertEqual(buyer_ref, 'DEPT-42')

    def test_buyer_reference_peppol_order_without_customer_reference(self):
        """ Without a customer reference on the order, the sale order name (seller's own number) must
        not leak into BuyerReference; PINT's default applies instead. """
        buyer_ref = self._get_buyer_reference({
            'l10n_sg_peppol_order_id': 'PO-0002',
        })
        self.assertEqual(buyer_ref, 'CUST-A')

    def test_buyer_reference_order_not_from_peppol(self):
        """ Orders not received over Peppol keep PINT's default. """
        buyer_ref = self._get_buyer_reference({
            'client_order_ref': 'DEPT-42',
        })
        self.assertEqual(buyer_ref, 'CUST-A')
