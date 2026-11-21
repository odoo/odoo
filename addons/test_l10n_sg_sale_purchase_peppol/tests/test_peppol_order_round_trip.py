from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPeppolOrderRoundTrip(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(su=True)
        cls.buyer_company = cls.env.company
        cls.buyer_company.partner_id.write({
            'vat': 'BE0477472701',
            'routing_scheme': '0208',
            'routing_endpoint': '0477472701',
        })
        cls.seller_company = cls.setup_other_company(name='Seller Company')['company']
        cls.seller_company.partner_id.write({'routing_scheme': '0088', 'routing_endpoint': '5880000000027'})
        cls.singapore = cls.env.ref('base.sg')
        cls.product = cls.env['product.product'].create({
            'name': 'Needle 4mm',
            'default_code': 'NDL4',
            'type': 'consu',
            'list_price': 50.0,
        })

    def _round_trip(self, **po_vals):
        po = self.env['purchase.order'].create({
            'partner_id': self.seller_company.partner_id.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_qty': 3.0, 'price_unit': 40.0})],
            **po_vals,
        })
        attachment = self.env['ir.attachment'].create({
            'name': 'order.xml',
            'raw': self.env['purchase.edi.xml.ubl_bis3_order'].build_order_xml(po),
            'mimetype': 'application/xml',
        })
        so = self.env['sale.order'].with_company(self.seller_company).with_context(
            default_partner_id=self.env.ref('base.public_partner').id,
        )._peppol_create_order_from_attachment(attachment)
        return po, so

    def _make_address(self, name, street, **vals):
        return self.env['res.partner'].create({
            'name': name,
            'street': street,
            'zip': '111111',
            'country_id': self.singapore.id,
            **vals,
        })

    def test_order_round_trip(self):
        """Test a purchase order exported through Peppol is imported as the same sale order on the
        seller side."""
        po, so = self._round_trip()
        self.assertRecordValues(so, [{
            'company_id': self.seller_company.id,
            'l10n_sg_peppol_order_id': po.name,
            'l10n_sg_peppol_buyer_endpoint': '0208:0477472701',
        }])
        self.assertEqual(so.partner_id.commercial_partner_id.routing_identifier, '0208:0477472701')
        self.assertRecordValues(so.order_line, [{
            'product_id': self.product.id,
            'product_uom_qty': 3.0,
            'price_unit': 40.0,
        }])

    def test_delivery_round_trip_warehouse(self):
        """Test the receiving warehouse of a purchase order becomes the delivery address of the
        sale order."""
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.buyer_company.id)], limit=1)
        warehouse.partner_id = self._make_address('Buyer Warehouse', '2 Warehouse Road')
        _po, so = self._round_trip(picking_type_id=warehouse.in_type_id.id)
        self.assertRecordValues(so.partner_shipping_id, [{
            'name': 'Buyer Warehouse',
            'street': '2 Warehouse Road',
            'parent_id': so.partner_id.commercial_partner_id.id,
            'type': 'delivery',
        }])

    def test_delivery_round_trip_dropship(self):
        """Test the dropship address of a purchase order takes precedence over its receiving
        warehouse as the delivery address of the sale order."""
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.buyer_company.id)], limit=1)
        warehouse.partner_id = self._make_address('Buyer Warehouse', '2 Warehouse Road')
        _po, so = self._round_trip(dest_address_id=self._make_address('End Customer', '3 Customer Road').id)
        self.assertRecordValues(so.partner_shipping_id, [{
            'name': 'End Customer',
            'street': '3 Customer Road',
        }])
