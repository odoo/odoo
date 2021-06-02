# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError



class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    @api.depends('quant_ids')
    def _compute_weight(self):
        for package in self:
            weight = 0.0
            if self.env.context.get('picking_id'):
                # TODO: potential bottleneck: N packages = N queries, use groupby ?
                current_picking_move_line_ids = self.env['stock.move.line'].search([
                    ('result_package_id', '=', package.id),
                    ('picking_id', '=', self.env.context['picking_id'])
                ])
                for ml in current_picking_move_line_ids:
                    weight += ml.product_uom_id._compute_quantity(
                        ml.qty_done, ml.product_id.uom_id) * ml.product_id.weight
            else:
                for quant in package.quant_ids:
                    weight += quant.quantity * quant.product_id.weight
            package.weight = weight

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package in self:
            package.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    weight = fields.Float(compute='_compute_weight', help="Total weight of all the products contained in the package.")
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)
    shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.")


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    @api.depends('move_line_ids', 'move_line_ids.result_package_id')
    def _compute_packages(self):
        for package in self:
            packs = set()
            for move_line in package.move_line_ids:
                if move_line.result_package_id:
                    packs.add(move_line.result_package_id.id)
            package.package_ids = list(packs)

    @api.depends('move_line_ids', 'move_line_ids.result_package_id', 'move_line_ids.product_uom_id', 'move_line_ids.qty_done')
    def _compute_bulk_weight(self):
        for picking in self:
            weight = 0.0
            for move_line in picking.move_line_ids:
                if move_line.product_id and not move_line.result_package_id:
                    weight += move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id) * move_line.product_id.weight
            picking.weight_bulk = weight

    @api.depends('package_ids', 'weight_bulk')
    def _compute_shipping_weight(self):
        for picking in self:
            picking.shipping_weight = picking.weight_bulk + sum([pack.shipping_weight for pack in picking.package_ids])

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package in self:
            package.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    carrier_price = fields.Float(string="Shipping Cost")
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier", check_company=True)
    volume = fields.Float(copy=False, digits='Volume')
    weight = fields.Float(compute='_cal_weight', digits='Stock Weight', store=True, help="Total weight of the products in the picking.", compute_sudo=True)
    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
    carrier_tracking_url = fields.Char(string='Tracking URL', compute='_compute_carrier_tracking_url')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)
    package_ids = fields.Many2many('stock.quant.package', compute='_compute_packages', string='Packages')
    weight_bulk = fields.Float('Bulk Weight', compute='_compute_bulk_weight')
    shipping_weight = fields.Float("Weight for Shipping", compute='_compute_shipping_weight', help="Total weight of the packages and products which are not in a package. That's the weight used to compute the cost of the shipping.")
    is_return_picking = fields.Boolean(compute='_compute_return_picking')
    return_label_ids = fields.One2many('ir.attachment', compute='_compute_return_label')

    @api.depends('carrier_id', 'carrier_tracking_ref')
    def _compute_carrier_tracking_url(self):
        for picking in self:
            picking.carrier_tracking_url = picking.carrier_id.get_tracking_link(picking) if picking.carrier_id and picking.carrier_tracking_ref else False

    @api.depends('carrier_id', 'move_ids_without_package')
    def _compute_return_picking(self):
        for picking in self:
            if picking.carrier_id and picking.carrier_id.can_generate_return:
                picking.is_return_picking = any(m.origin_returned_move_id for m in picking.move_ids_without_package)
            else:
                picking.is_return_picking = False

    def _compute_return_label(self):
        for picking in self:
            if picking.carrier_id:
                picking.return_label_ids = self.env['ir.attachment'].search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id), ('name', 'like', '%s%%' % picking.carrier_id.get_return_label_prefix())])
            else:
                picking.return_label_ids = False

    def get_multiple_carrier_tracking(self):
        self.ensure_one()
        try:
            return json.loads(self.carrier_tracking_url)
        except (ValueError, TypeError):
            return False

    @api.depends('move_lines')
    def _cal_weight(self):
        for picking in self:
            picking.weight = sum(move.weight for move in picking.move_lines if move.state != 'cancel')

    def _send_confirmation_email(self):
        for pick in self:
            if pick.carrier_id:
                if pick.carrier_id.integration_level == 'rate_and_ship' and pick.picking_type_code != 'incoming':
                    pick.send_to_shipper()
        return super(StockPicking, self)._send_confirmation_email()

    def _pre_put_in_pack_hook(self, move_line_ids):
        res = super(StockPicking, self)._pre_put_in_pack_hook(move_line_ids)
        if not res:
            if self.carrier_id:
                return self._set_delivery_packaging()
        else:
            return res

    def _set_delivery_packaging(self):
        """ This method returns an action allowing to set the product packaging and the shipping weight
         on the stock.quant.package.
        """
        self.ensure_one()
        view_id = self.env.ref('delivery.choose_delivery_package_view_form').id
        context = dict(
            self.env.context,
            current_package_carrier_type=self.carrier_id.delivery_type,
            default_picking_id=self.id
        )
        # As we pass the `delivery_type` ('fixed' or 'base_on_rule' by default) in a key who
        # correspond to the `package_carrier_type` ('none' to default), we make a conversion.
        # No need conversion for other carriers as the `delivery_type` and
        #`package_carrier_type` will be the same in these cases.
        if context['current_package_carrier_type'] in ['fixed', 'base_on_rule']:
            context['current_package_carrier_type'] = 'none'
        return {
            'name': _('Package Details'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.package',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': context,
        }

    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping(self)[0]
        if self.carrier_id.free_over and self.sale_id and self.sale_id._compute_amount_total_without_delivery() >= self.carrier_id.amount:
            res['exact_price'] = 0.0
        self.carrier_price = res['exact_price'] * (1.0 + (self.carrier_id.margin / 100.0))
        if res['tracking_number']:
            self.carrier_tracking_ref = res['tracking_number']
        order_currency = self.sale_id.currency_id or self.company_id.currency_id
        msg = _("Shipment sent to carrier %s for shipping with tracking number %s<br/>Cost: %.2f %s") % (self.carrier_id.name, self.carrier_tracking_ref, self.carrier_price, order_currency.name)
        self.message_post(body=msg)
        self._add_delivery_cost_to_so()

    def print_return_label(self):
        self.ensure_one()
        res = self.carrier_id.get_return_label(self)

    def _add_delivery_cost_to_so(self):
        self.ensure_one()
        sale_order = self.sale_id
        if sale_order and self.carrier_id.invoice_policy == 'real' and self.carrier_price:
            delivery_lines = sale_order.order_line.filtered(lambda l: l.is_delivery and l.currency_id.is_zero(l.price_unit) and l.product_id == self.carrier_id.product_id)
            carrier_price = self.carrier_price * (1.0 + (float(self.carrier_id.margin) / 100.0))
            if not delivery_lines:
                sale_order._create_delivery_line(self.carrier_id, carrier_price)
            else:
                delivery_line = delivery_lines[0]
                delivery_line[0].write({
                    'price_unit': carrier_price,
                    # remove the estimated price from the description
                    'name': sale_order.carrier_id.with_context(lang=self.partner_id.lang).name,
                })

    def open_website_url(self):
        self.ensure_one()
        if not self.carrier_tracking_url:
            raise UserError(_("Your delivery method has no redirect on courier provider's website to track this order."))

        carrier_trackers = []
        try:
            carrier_trackers = json.loads(self.carrier_tracking_url)
        except ValueError:
            carrier_trackers = self.carrier_tracking_url
        else:
            msg = "Tracking links for shipment: <br/>"
            for tracker in carrier_trackers:
                msg += '<a href=' + tracker[1] + '>' + tracker[0] + '</a><br/>'
            self.message_post(body=msg)
            return self.env.ref('delivery.act_delivery_trackers_url').read()[0]

        client_action = {
            'type': 'ir.actions.act_url',
            'name': "Shipment Tracking Page",
            'target': 'new',
            'url': self.carrier_tracking_url,
        }
        return client_action

    def cancel_shipment(self):
        for picking in self:
            picking.carrier_id.cancel_shipment(self)
            msg = "Shipment %s cancelled" % picking.carrier_tracking_ref
            picking.message_post(body=msg)
            picking.carrier_tracking_ref = False

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

    def _create_returns(self):
        # Prevent copy of the carrier and carrier price when generating return picking
        # (we have no integration of returns for now)
        new_picking, pick_type_id = super(StockReturnPicking, self)._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        picking.write({'carrier_id': False,
                       'carrier_price': 0.0})
        return new_picking, pick_type_id
