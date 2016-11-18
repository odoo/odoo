# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import odoo.addons.decimal_precision as dp


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
    shipping_weight = fields.Float(string='Shipping Weight', help="Can be changed during the 'put in pack' to adjust the weight of the shipping.")


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    @api.multi
    def manage_package_type(self):
        self.ensure_one()
        return {
            'name': _('Package Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.quant.package',
            'view_id': self.env.ref('delivery.view_quant_package_form_save').id,
            'target': 'new',
            'res_id': self.result_package_id.id,
            'context': {
                'current_package_carrier_type': self.picking_id.carrier_id.delivery_type if self.picking_id.carrier_id.delivery_type not in ['base_on_rule', 'fixed'] else 'none',
            },
        }


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
        for packop in self.pack_operation_ids:
            if packop.product_id and not packop.result_package_id:
                weight += packop.product_uom_id._compute_quantity(packop.product_qty, packop.product_id.uom_id) * packop.product_id.weight
        self.weight_bulk = weight

    @api.one
    @api.depends('package_ids', 'weight_bulk')
    def _compute_shipping_weight(self):
        self.shipping_weight = self.weight_bulk + sum([pack.shipping_weight for pack in self.package_ids])

    carrier_price = fields.Float(string="Shipping Cost")
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier")
    volume = fields.Float(copy=False)
    weight = fields.Float(compute='_cal_weight', digits=dp.get_precision('Stock Weight'), store=True)
    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
    number_of_packages = fields.Integer(string='Number of Packages', copy=False)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly="1", help="Unit of measurement for Weight", default=_default_uom)
    package_ids = fields.Many2many('stock.quant.package', compute='_compute_packages', string='Packages')
    weight_bulk = fields.Float('Bulk Weight', compute='_compute_bulk_weight')
    shipping_weight = fields.Float("Weight for Shipping", compute='_compute_shipping_weight')

    @api.onchange('carrier_id')
    def onchange_carrier(self):
        if self.carrier_id.delivery_type in ['fixed', 'base_on_rule']:
            order = self.sale_id
            if order:
                self.carrier_price = self.carrier_id.get_price_available(order)
            else:
                self.carrier_price = self.carrier_id.price

    @api.depends('product_id', 'move_lines')
    def _cal_weight(self):
        for picking in self:
            picking.weight = sum(move.weight for move in picking.move_lines if move.state != 'cancel')

    @api.multi
    def do_transfer(self):
        # TDE FIXME: should work in batch
        self.ensure_one()
        res = super(StockPicking, self).do_transfer()

        if self.carrier_id and self.carrier_id.delivery_type not in ['fixed', 'base_on_rule'] and self.carrier_id.integration_level == 'rate_and_ship':
            self.send_to_shipper()

        if self.carrier_id:
            self._add_delivery_cost_to_so()

        return res

    @api.multi
    def put_in_pack(self):
        # TDE FIXME: work in batch, please
        self.ensure_one()
        package = super(StockPicking, self).put_in_pack()

        current_package_carrier_type = self.carrier_id.delivery_type if self.carrier_id.delivery_type not in ['base_on_rule', 'fixed'] else 'none'
        count_packaging = self.env['product.packaging'].search_count([('package_carrier_type', '=', current_package_carrier_type)])
        if not count_packaging:
            return False
        # By default, sum the weights of all package operations contained in this package
        pack_operation_ids = self.env['stock.pack.operation'].search([('result_package_id', '=', package.id)])
        package_weight = sum([x.qty_done * x.product_id.weight for x in pack_operation_ids])
        package.shipping_weight = package_weight

        return {
            'name': _('Package Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.quant.package',
            'view_id': self.env.ref('delivery.view_quant_package_form_save').id,
            'target': 'new',
            'res_id': package.id,
            'context': {
                'current_package_carrier_type': current_package_carrier_type,
            },
        }

    @api.multi
    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping(self)[0]
        self.carrier_price = res['exact_price']
        self.carrier_tracking_ref = res['tracking_number']
        order_currency = self.sale_id.currency_id or self.company_id.currency_id
        msg = _("Shipment sent to carrier %s for shipping with tracking number %s<br/>Cost: %.2f %s") % (self.carrier_id.name, self.carrier_tracking_ref, self.carrier_price, order_currency.name)
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
        if self.carrier_id.get_tracking_link(self):
            url = self.carrier_id.get_tracking_link(self)[0]
        else:
            raise UserError(_("Your delivery method has no redirect on courier provider's website to track this order."))

        client_action = {'type': 'ir.actions.act_url',
                         'name': "Shipment Tracking Page",
                         'target': 'new',
                         'url': url,
                         }
        return client_action

    @api.one
    def cancel_shipment(self):
        self.carrier_id.cancel_shipment(self)
        msg = "Shipment %s cancelled" % self.carrier_tracking_ref
        self.message_post(body=msg)
        self.carrier_tracking_ref = False

    @api.multi
    def check_packages_are_identical(self):
        '''Some shippers require identical packages in the same shipment. This utility checks it.'''
        self.ensure_one()
        if self.package_ids:
            packages = [p.packaging_id for p in self.package_ids]
            if len(set(packages)) != 1:
                package_names = ', '.join([str(p.name) for p in packages])
                raise UserError(_('You are shipping different packaging types in the same shipment.\nPackaging Types: %s' % package_names))
        return True


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.multi
    def _create_returns(self):
        # Prevent copy of the carrier and carrier price when generating return picking
        # (we have no integration of returns for now)
        new_picking, pick_type_id = super(StockReturnPicking, self)._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        picking.write({'carrier_id': False,
                       'carrier_price': 0.0})
        return new_picking, pick_type_id
