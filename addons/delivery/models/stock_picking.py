# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from openerp.exceptions import UserError

import openerp.addons.decimal_precision as dp


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    carrier_price = fields.Float(string="Shipping Cost", readonly=True)
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier")
    volume = fields.Float(copy=False)
    weight = fields.Float(compute='_cal_weight', digits_compute=dp.get_precision('Stock Weight'), store=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    number_of_packages = fields.Integer(string='Number of Packages', copy=False)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly="1", help="Unit of measurement for Weight", default=_default_uom)

    @api.depends('product_id', 'move_lines')
    def _cal_weight(self):
        for picking in self:
            picking.weight = sum(move.weight for move in picking.move_lines if move.state != 'cancel')

    @api.multi
    def do_transfer(self):
        self.ensure_one()
        res = super(StockPicking, self).do_transfer()

        if self.carrier_id and self.carrier_id.delivery_type not in ['fixed', 'base_on_rule']:
            self.send_to_shipper()
        return res

    @api.multi
    def _prepare_shipping_invoice_line(self, invoice):
        self.ensure_one()
        invoice.ensure_one()

        carrier = self.carrier_id

        # No carrier
        if not carrier:
            return None
        # Carrier already invoiced on the sale order
        if any(inv_line.product_id.id == carrier.product_id.id for inv_line in invoice.invoice_line_ids):
            return None

        # Classic carrier
        if carrier.delivery_type in ['fixed', 'base_on_rule']:
            carrier = carrier.verify_carrier(self.partner_id)
            if not carrier:
                raise UserError(_('The carrier %s (id: %d) has no delivery method!') % (self.carrier_id.name, self.carrier_id.id))
            quantity = sum([line.product_uom_qty for line in self.move_lines])
            price = carrier.get_price_from_picking(invoice.amount_untaxed, self.weight, self.volume, quantity)
        else:
            # Shipping provider
            price = self.carrier_price

        if invoice.company_id.currency_id.id != invoice.currency_id.id:
            price = invoice.company_id.currency_id.with_context(date=invoice.date_invoice).compute(invoice.currency_id.id, price)
        account_id = carrier.product_id.property_account_income.id
        if not account_id:
            account_id = carrier.product_id.categ_id.property_account_income_categ.id

        taxes = carrier.product_id.taxes_id
        taxes_ids = taxes.ids

        # Apply original SO fiscal position
        if self.sale_id.fiscal_position_id:
            fpos = self.sale_id.fiscal_position_id
            account_id = fpos.map_account(account_id)
            taxes_ids = fpos.map_tax(taxes).ids

        res = {
            'name': carrier.name,
            'invoice_id': invoice.id,
            'uom_id': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'account_id': account_id,
            'price_unit': price,
            'quantity': 1,
            'invoice_line_tax_ids': [(6, 0, taxes_ids)],
        }

        return res

    @api.model
    def _invoice_create_line(self, moves, journal_id, inv_type='out_invoice'):
        InvoiceLine = self.env['account.invoice.line']
        invoice_ids = super(StockPicking, self)._invoice_create_line(moves, journal_id, inv_type=inv_type)
        for move in moves:
            for invoice in move.picking_id.sale_id.invoice_ids.filtered(lambda invoice: invoice.id in invoice_ids):
                invoice_line = move.picking_id._prepare_shipping_invoice_line(invoice)
                if invoice_line:
                    InvoiceLine.create(invoice_line)
        return invoice_ids

    @api.multi
    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping(self)[0]
        self.carrier_price = res['exact_price']
        self.carrier_tracking_ref = res['tracking_number']
        msg = _("Shipment sent to carrier %s for expedition with tracking number %s") % (self.carrier_id.name, self.carrier_tracking_ref)
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
