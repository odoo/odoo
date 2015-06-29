# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('product_id', 'move_lines')
    def _cal_weight(self):
        for picking in self:
            total_weight = total_weight_net = 0.00

            for move in picking.move_lines:
                total_weight += move.weight
                total_weight_net += move.weight_net

                move.total_weight = total_weight
                move.total_weight_net = total_weight_net

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    @api.multi
    def _get_picking_line(self):
        result = {}
        for line in self.env['stock.move']:
            result[line.picking_id.id] = True
        return result.keys()

    carrier_price = fields.Float(string="Shipping Cost", readonly=True)
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier')
    volume = fields.Float(copy=False)
    weight = fields.Float(compute='_cal_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_net = fields.Float(compute='_cal_weight', string='Net Weight', digits=dp.get_precision('Stock Weight'), store=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    number_of_packages = fields.Integer(string='Number of Packages', copy=False)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, help="Unit of measurement for Weight", default=_default_uom)

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()

        if self.carrier_id and self.carrier_id.delivery_type != 'grid':
            self.send_to_shipper()
        return res

    # Signature due to strange old api methods
    @api.model
    def _prepare_shipping_invoice_line(self, picking, invoice):
        picking.ensure_one()
        invoice.ensure_one()

        carrier = picking.carrier_id

        # No carrier
        if not carrier:
            return None
        # Carrier already invoiced on the sale order
        if any(inv_line.product_id.id == carrier.product_id.id for inv_line in invoice.invoice_line_ids):
            return None

        # Classic carrier
        if carrier.delivery_type == 'grid':
            grid_id = carrier.grid_get(picking.partner_id.id)
            if not grid_id:
                raise UserError(_('The carrier %s (id: %d) has no delivery grid!') % (picking.carrier_id.name, picking.carrier_id.id))

        # Shipping provider
        price = picking.carrier_price

        account_id = carrier.product_id.property_account_income.id
        if not account_id:
            account_id = carrier.product_id.categ_id.property_account_income_categ.id

        taxes = carrier.product_id.taxes_id
        taxes_ids = taxes.ids

        # Apply original SO fiscal position
        if picking.sale_id.fiscal_position_id:
            fpos = picking.sale_id.fiscal_position_id
            account_id = fpos.map_account(account_id)
            taxes_ids = fpos.map_tax(taxes).ids

        res = {
            'name': carrier.name,
            'invoice_id': invoice.id,
            'uos_id': carrier.product_id.uos_id.id,
            'product_id': carrier.product_id.id,
            'account_id': account_id,
            'price_unit': price,
            'quantity': 1,
            'invoice_line_tax_id': [(6, 0, taxes_ids)],
        }

        return res

    @api.model
    def _invoice_create_line(self, moves, journal_id, inv_type='out_invoice'):
        InvoiceLine = self.env['account.invoice.line']
        invoice_ids = super(StockPicking, self)._invoice_create_line(moves, journal_id, inv_type=inv_type)
        delivey_invoices = {}
        for move in moves:
            for invoice in move.picking_id.sale_id.invoice_ids:
                if invoice.id in invoice_ids:
                    delivey_invoices[invoice] = move.picking_id
        if delivey_invoices:
            for invoice, picking in delivey_invoices.items():
                invoice_line = self._prepare_shipping_invoice_line(picking, invoice)
                if invoice_line:
                    InvoiceLine.create(invoice_line)
        return invoice_ids

    @api.one
    def send_to_shipper(self):
        res = self.carrier_id.send_shipping(self)[0]
        self.carrier_price = res['exact_price']
        self.carrier_tracking_ref = res['tracking_number']
        msg = "Shipment sent to carrier %s for expedition with tracking number %s" % (self.carrier_id.name, self.carrier_tracking_ref)
        self.message_post(body=msg)

    @api.multi
    def open_website_url(self):
        self.ensure_one()

        client_action = {'type': 'ir.actions.act_url',
                         'name': "Shipment Tracking Page",
                         'target': 'new',
                         'url': self.carrier_id.get_tracking_link(self)[0]
                         }
        return client_action

    @api.one
    def cancel_shipment(self):
        self.carrier_id.cancel_shipment(self)
        msg = "Shipment %s cancelled" % self.carrier_tracking_ref
        self.message_post(body=msg)
        self.carrier_tracking_ref = False
