# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (c) 2015 Odoo S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
            return super(StockPicking, self)._prepare_shipping_invoice_line(picking, invoice)

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

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    weight = fields.Float(compute='_cal_move_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_net = fields.Float(compute='_cal_move_weight', string='Net weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight", default=_default_uom)

    @api.depends('product_id')
    def _cal_move_weight(self):
        for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
            weight = weight_net = 0.00
            converted_qty = move.product_qty
            weight = (converted_qty * move.product_id.weight)

            if move.product_id.weight_net > 0.00:
                weight_net = (converted_qty * move.product_id.weight_net)

            move.weight = weight
            move.weight_net = weight_net

    @api.multi
    def action_confirm(self):
        """
            Pass the carrier to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the
                original move is deleted)
        """
        procs_to_check = []
        for move in self:
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.carrier_id:
                procs_to_check += [move.procurement_id]
        res = super(StockMove, self).action_confirm()
        StockPiking = self.env["stock.picking"]
        for proc in procs_to_check:
            pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.carrier_id]))
            if pickings:
                StockPiking.write({'carrier_id': proc.sale_line_id.order_id.carrier_id.id})
        return res
