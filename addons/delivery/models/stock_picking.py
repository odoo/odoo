# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from openerp.exceptions import UserError

import openerp.addons.decimal_precision as dp

class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    @api.one
    @api.depends('quant_ids', 'children_ids')
    def _compute_weight(self):
        weight = 0
        for quant in self.quant_ids:
            weight += quant.qty * quant.product_id.weight
        for pack in self.children_ids:
            pack._compute_weight()
            weight += pack.weight
        self.weight = weight

    weight = fields.Float(compute='_compute_weight')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    @api.one
    @api.depends('pack_operation_ids')
    def _compute_packages(self):
        self.ensure_one()
        packs = set()
        for packop in self.pack_operation_ids:
            if packop.result_package_id:
                packs.add(packop.result_package_id.id)
            elif packop.package_id and not packop.product_id:
                packs.add(packop.package_id.id)
        self.package_ids = list(packs)

    @api.one
    @api.depends('pack_operation_ids')
    def _compute_bulk_weight(self):
        weight = 0.0
        uom_obj = self.env['product.uom']
        for packop in self.pack_operation_ids:
            if packop.product_id and not packop.result_package_id:
                weight += uom_obj._compute_qty_obj(packop.product_uom_id , packop.product_qty, packop.product_id.uom_id) * packop.product_id.weight
        self.weight_bulk = weight

    carrier_price = fields.Float(string="Shipping Cost", readonly=True)
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier")
    volume = fields.Float(copy=False)
    weight = fields.Float(compute='_cal_weight', digits=dp.get_precision('Stock Weight'), store=True)
    carrier_tracking_ref = fields.Char(string='Carrier Tracking Ref', copy=False)
    number_of_packages = fields.Integer(string='Number of Packages', copy=False)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly="1", help="Unit of measurement for Weight", default=_default_uom)
    package_ids = fields.Many2many('stock.quant.package', compute='_compute_packages', string='Packages')
    weight_bulk = fields.Float('Bulk Weight', compute='_compute_bulk_weight')

    @api.depends('product_id', 'move_lines')
    def _cal_weight(self):
        for picking in self:
            picking.weight = sum(move.weight for move in picking.move_lines if move.state != 'cancel')

    @api.multi
    def do_transfer(self):
        self.ensure_one()
        res = super(StockPicking, self).do_transfer()

        if self.carrier_id and self.carrier_id.delivery_type not in ['fixed', 'base_on_rule'] and self.carrier_id.shipping_enabled:
            self.send_to_shipper()
            self._add_delivery_cost_to_so()

        return res

    @api.multi
    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping(self)[0]
        self.carrier_price = res['exact_price']
        self.carrier_tracking_ref = res['tracking_number']
        msg = _("Shipment sent to carrier %s for expedition with tracking number %s") % (self.carrier_id.name, self.carrier_tracking_ref)
        self.message_post(body=msg)

    @api.multi
    def _add_delivery_cost_to_so(self):
        self.ensure_one()
        sale_order = self.sale_id
        if sale_order.invoice_shipping_on_delivery:
            sale_order._create_delivery_line(self.carrier_id, self.carrier_price)

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
