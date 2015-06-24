# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError

import openerp.addons.decimal_precision as dp

# Overloaded stock_picking to manage carriers :


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

    carrier_id = fields.Many2one('delivery.carrier', string='Carrier')
    volume = fields.Float(copy=False)
    weight = fields.Float(compute='_cal_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_net = fields.Float(compute='_cal_weight', string='Net Weight', digits=dp.get_precision('Stock Weight'), store=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    number_of_packages = fields.Integer(string='Number of Packages', copy=False)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True,
        readonly=True, help="Unit of measurement for Weight", default=_default_uom)

    @api.one
    def _prepare_shipping_invoice_line(self, picking, invoice):
        """Prepare the invoice line to add to the shipping costs to the
        shipping's invoice.
            :param browse_record picking: the stock picking being invoiced
            :param browse_record invoice: the stock picking's invoice
            :return: dict containing the values to create the invoice line,
                     or None to create nothing
        """
        Carrrier = self.env['delivery.carrier']
        Grid = self.env['delivery.grid']
        if not picking.carrier_id or \
            any(inv_line.product_id.id == picking.carrier_id.product_id.id
                for inv_line in invoice.invoice_line_ids):
            return None
        grid_id = Carrrier.grid_get(picking.partner_id.id)
        if not grid_id:
            raise UserError(_('The carrier %s (id: %d) has no delivery grid!') %
                (picking.carrier_id.name, picking.carrier_id.id))
        quantity = sum([line.product_uom_qty for line in picking.move_lines])
        price = Grid.get_price_from_picking(invoice.amount_untaxed, picking.weight, picking.volume, quantity)
        account_id = picking.carrier_id.product_id.property_account_income.id
        if not account_id:
            account_id = picking.carrier_id.product_id.categ_id.property_account_income_categ.id

        taxes = picking.carrier_id.product_id.taxes_id
        partner = picking.partner_id or False
        if partner:
            account_id = self.env['account.fiscal.position'].map_account(partner.property_account_position, account_id)
            taxes_ids = self.env['account.fiscal.position'].map_tax(partner.property_account_position, taxes)
        else:
            taxes_ids = [x.id for x in taxes]

        return {
            'name': picking.carrier_id.name,
            'invoice_id': invoice.id,
            'uos_id': picking.carrier_id.product_id.uos_id.id,
            'product_id': picking.carrier_id.product_id.id,
            'account_id': account_id,
            'price_unit': price,
            'quantity': 1,
            'invoice_line_tax_ids': [(6, 0, taxes_ids)],
        }

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
