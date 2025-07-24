from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestAr
from odoo.addons.mail.tests.common import MailCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestArDeliveryGuide(TestAr, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data['company'].id)])
        cls.stock_location = cls.env['stock.location'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('usage', '=', 'internal')
        ], limit=1)
        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.product_pc = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0
        })
        cls.picking_type = cls.env['stock.picking.type'].create({
            'name': 'Remito Outgoing',
            'code': 'outgoing',
            'company_id': cls.company.id,
            'sequence_code': 'OUT',
            'l10n_ar_document_type_id': cls.env.ref('l10n_ar.dc_r_r').id,
            'l10n_ar_cai_authorization_code': '1234567890',
            'l10n_ar_cai_expiration_date': '2025-12-31',
            'l10n_ar_sequence_number_start': '00000001',
            'l10n_ar_sequence_number_end': '00000999',
        })

    def _get_stock_picking_move_line_vals(self):
        """Default values for creating stock picking move lines."""
        return [Command.create({
            'product_id': self.product_pc.id,
            'product_uom_qty': 1.0,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })]

    def _get_stock_picking_vals(self, move_lines_args=None):
        """Default values for creating a stock picking."""
        return {
            'location_id': self.wh.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type.id,
            'partner_id': self.partner_ri.id,
            'move_ids': move_lines_args or self._get_stock_picking_move_line_vals(),
        }

    def get_stock_picking(self, stock_picking_args=None, move_lines_args=None):
        """Create and validate a stock picking."""
        stock_picking_vals = self._get_stock_picking_vals(move_lines_args)
        if stock_picking_args:
            stock_picking_vals.update(stock_picking_args)
        stock_picking = self.env['stock.picking'].create(stock_picking_vals)
        stock_picking.action_confirm()
        stock_picking.button_validate()
        return stock_picking

    def test_delivery_guide_creation_and_mail(self):
        """Test the creation of a delivery guide number and sending it via email."""
        stock_picking = self.get_stock_picking()

        # Delivery Guide number creation and storing CAI data
        stock_picking.l10n_ar_action_create_delivery_guide()

        self.assertTrue(stock_picking.l10n_ar_delivery_guide_number, "Delivery guide number should be set.")
        self.assertIn(
            self.picking_type.l10n_ar_delivery_sequence_prefix or '',
            stock_picking.l10n_ar_delivery_guide_number,
            "Delivery guide number should include the configured prefix."
        )

        with self.mock_mail_gateway():
            stock_picking.l10n_ar_action_send_delivery_guide()

        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(
            self._new_mails.subject,
            f"{stock_picking.company_id.name} Document (Ref {stock_picking.l10n_ar_delivery_guide_number})"
        )
        self.assertEqual(
            f'Remito - {stock_picking.l10n_ar_delivery_guide_number}.pdf',
            self._new_mails.attachment_ids.name,
            "Email should contain the delivery guide PDF attachment."
        )
