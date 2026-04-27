from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ec_edi.tests.test_edi_xml import TestEcEdiXmls


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestECDeliveryGuideCommon(TestEcEdiXmls):

    @classmethod
    def setUpClass(cls):
        '''
        Set up test variables
        '''
        super().setUpClass()
        cls.chart_template_ref = 'l10n_ec.l10n_ec_ifrs'
        cls.edi_format_ref = 'l10n_ec_edi.ecuadorian_edi_format'

        cls.wh = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data['company'].id)])
        cls.stock_location = cls.env['stock.location'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('usage', '=', 'internal')
        ], limit=1)
        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.product_pc = cls.env['product.product'].create({
            'name': 'Computadora',
            'list_price': 320.0
        })

        cls.delivery_guide_carrier = cls.env['res.partner'].create({
            'name': 'Delivery guide Carrier EC',
            'l10n_latam_identification_type_id': cls.env.ref('l10n_ec.ec_dni').id,
            'vat': '0750032310'
        })

    def _get_stock_picking_move_line_vals(self):
        '''
        Default values for creating stock picking move lines
        '''
        return [Command.create({
            'product_id': self.product_pc.id,
            'name': '[A12345] Computadora',
            'product_uom_qty': 1.0,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        })]

    def _get_stock_picking_vals(self, move_lines_args):
        '''
        Default values for creating a stock picking
        '''
        return {
            'location_id': self.wh.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.wh.out_type_id.id,
            'partner_id': self.partner_a.id,
            'move_ids_without_package': move_lines_args,
        }

    def get_stock_picking(self, stock_picking_args=None, move_lines_args=None):
        '''
        Method that creates the stock picking according to arguments
        '''
        if move_lines_args is None:
            move_lines_args = self._get_stock_picking_move_line_vals()
        stock_picking_vals = self._get_stock_picking_vals(move_lines_args)
        if stock_picking_args:
            stock_picking_vals.update(stock_picking_args)
        stock_picking = self.env['stock.picking'].create({
            **stock_picking_vals,
        })
        stock_picking.action_confirm()
        return stock_picking

    def prepare_delivery_guide(self, stock_picking):
        '''
        Method that set the delivery guide data and send the delivery guide
        '''
        stock_picking.action_confirm()
        stock_picking.button_validate()
        stock_picking.write({
            'l10n_ec_transporter_id': self.delivery_guide_carrier.id,
            'l10n_ec_plate_number': 'OBA-1413',
        })
        stock_picking.picking_type_id.warehouse_id.write({
            'l10n_ec_entity': '001',
            'l10n_ec_emission': '001',
        })
        stock_picking.l10n_ec_action_create_delivery_guide()
        stock_picking.l10n_ec_send_delivery_guide_to_send()
