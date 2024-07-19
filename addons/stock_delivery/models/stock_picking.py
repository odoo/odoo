# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from markupsafe import Markup
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.sql import column_exists, create_column


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_picking", "weight"):
            # In order to speed up module installation when dealing with hefty data
            # We create the column weight manually, but the computation will be skipped
            # Therefore we do the computation in a query by getting weight sum from stock moves
            create_column(self.env.cr, "stock_picking", "weight", "numeric")
            self.env.cr.execute("""
                WITH computed_weight AS (
                    SELECT SUM(weight) AS weight_sum, picking_id
                    FROM stock_move
                    WHERE picking_id IS NOT NULL
                    GROUP BY picking_id
                )
                UPDATE stock_picking
                SET weight = weight_sum
                FROM computed_weight
                WHERE stock_picking.id = computed_weight.picking_id;
            """)
        return super()._auto_init()

    @api.depends('move_line_ids', 'move_line_ids.result_package_id')
    def _compute_packages(self):
        counts = dict(self.env['stock.move.line']._read_group(
           domain=[
              ('picking_id', 'in', self.ids),
              ('result_package_id', '!=', False)],
              groupby=['picking_id'],
              aggregates=['__count'],
        ))
        self.fetch(['move_line_ids'])
        self.move_line_ids.fetch(['result_package_id'])
        for picking in self:
            packs = set()
            if counts.get(picking, 0):
                for move_line in picking.move_line_ids:
                    if move_line.result_package_id:
                        packs.add(move_line.result_package_id.id)
            picking.package_ids = list(packs)

    @api.depends('move_line_ids', 'move_line_ids.result_package_id', 'move_line_ids.product_uom_id', 'move_line_ids.quantity')
    def _compute_bulk_weight(self):
        picking_weights = defaultdict(float)
        res_groups = self.env['stock.move.line']._read_group(
            [('picking_id', 'in', self.ids), ('product_id', '!=', False), ('result_package_id', '=', False)],
            ['picking_id', 'product_id', 'product_uom_id', 'quantity'],
            ['__count'],
        )
        for picking, product, product_uom, quantity, count in res_groups:
            picking_weights[picking.id] += (
                count
                * product_uom._compute_quantity(quantity, product.uom_id)
                * product.weight
            )
        for picking in self:
            picking.weight_bulk = picking_weights[picking.id]

    @api.depends('move_line_ids.result_package_id', 'move_line_ids.result_package_id.shipping_weight', 'weight_bulk')
    def _compute_shipping_weight(self):
        for picking in self:
            # if shipping weight is not assigned => default to calculated product weight
            picking.shipping_weight = (
                picking.weight_bulk +
                sum(pack.shipping_weight or pack.weight for pack in picking.package_ids.sudo())
            )

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package in self:
            package.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    carrier_price = fields.Float(string="Shipping Cost")
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier", check_company=True)
    weight = fields.Float(compute='_cal_weight', digits='Stock Weight', store=True, help="Total weight of the products in the picking.", compute_sudo=True)
    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
    carrier_tracking_url = fields.Char(string='Tracking URL', compute='_compute_carrier_tracking_url')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)
    package_ids = fields.Many2many('stock.quant.package', compute='_compute_packages', string='Packages')
    weight_bulk = fields.Float('Bulk Weight', compute='_compute_bulk_weight', help="Total weight of products which are not in a package.")
    shipping_weight = fields.Float("Weight for Shipping", compute='_compute_shipping_weight',
        help="Total weight of packages and products not in a package. Packages with no shipping weight specified will default to their products' total weight. This is the weight used to compute the cost of the shipping.")
    is_return_picking = fields.Boolean(compute='_compute_return_picking')
    return_label_ids = fields.One2many('ir.attachment', compute='_compute_return_label')
    destination_country_code = fields.Char(related='partner_id.country_id.code', string="Destination Country")

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
                picking.return_label_ids = self.env['ir.attachment'].search([('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id), ('name', '=like', '%s%%' % picking.carrier_id.get_return_label_prefix())])
            else:
                picking.return_label_ids = False

    def get_multiple_carrier_tracking(self):
        self.ensure_one()
        try:
            return json.loads(self.carrier_tracking_url)
        except (ValueError, TypeError):
            return False

    @api.depends('move_ids.weight')
    def _cal_weight(self):
        for picking in self:
            picking.weight = sum(move.weight for move in picking.move_ids if move.state != 'cancel')

    def _send_confirmation_email(self):
        for pick in self:
            if pick.carrier_id and pick.carrier_id.integration_level == 'rate_and_ship' and pick.picking_type_code != 'incoming' and not pick.carrier_tracking_ref and pick.picking_type_id.print_label:
                pick.sudo().send_to_shipper()
            pick._check_carrier_details_compliance()
        return super(StockPicking, self)._send_confirmation_email()

    def _pre_put_in_pack_hook(self, move_line_ids):
        res = super(StockPicking, self)._pre_put_in_pack_hook(move_line_ids)
        if not res:
            if move_line_ids.carrier_id:
                if len(move_line_ids.carrier_id) > 1 or any(not ml.carrier_id for ml in move_line_ids):
                    # avoid (duplicate) costs for products
                    raise UserError(_("You cannot pack products into the same package when they have different carriers (i.e. check that all of their transfers have a carrier assigned and are using the same carrier)."))
                return self._set_delivery_package_type(batch_pack=len(move_line_ids.picking_id) > 1)
        else:
            return res

    def _set_delivery_package_type(self, batch_pack=False):
        """ This method returns an action allowing to set the package type and the shipping weight
        on the stock.quant.package.
        """
        self.ensure_one()
        view_id = self.env.ref('stock_delivery.choose_delivery_package_view_form').id
        context = dict(
            self.env.context,
            current_package_carrier_type=self.carrier_id.delivery_type,
            default_picking_id=self.id,
            batch_pack=batch_pack,
        )
        # As we pass the `delivery_type` ('fixed' or 'base_on_rule' by default) in a key who
        # correspond to the `package_carrier_type` ('none' to default), we make a conversion.
        # No need conversion for other carriers as the `delivery_type` and
        #`package_carrier_type` will be the same in these cases.
        if context['current_package_carrier_type'] in ['fixed', 'base_on_rule']:
            context['current_package_carrier_type'] = 'none'
        # Update the context 'default_package_type_id' passed from JS
        # to populate the scanned package type in the package wizard opened from the barcode.
        if self.env.context.get('default_package_type_id'):
            context['default_delivery_package_type_id'] = self.env.context.get('default_package_type_id')
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
        if self.carrier_id.free_over and self.sale_id:
            amount_without_delivery = self.sale_id._compute_amount_total_without_delivery()
            if self.carrier_id._compute_currency(self.sale_id, amount_without_delivery, 'pricelist_to_company') >= self.carrier_id.amount:
                res['exact_price'] = 0.0
        self.carrier_price = self.carrier_id._apply_margins(res['exact_price'])
        if res['tracking_number']:
            related_pickings = self.env['stock.picking'] if self.carrier_tracking_ref and res['tracking_number'] in self.carrier_tracking_ref else self
            accessed_moves = previous_moves = self.move_ids.move_orig_ids
            while previous_moves:
                related_pickings |= previous_moves.picking_id
                previous_moves = previous_moves.move_orig_ids - accessed_moves
                accessed_moves |= previous_moves
            accessed_moves = next_moves = self.move_ids.move_dest_ids
            while next_moves:
                related_pickings |= next_moves.picking_id
                next_moves = next_moves.move_dest_ids - accessed_moves
                accessed_moves |= next_moves
            without_tracking = related_pickings.filtered(lambda p: not p.carrier_tracking_ref)
            without_tracking.carrier_tracking_ref = res['tracking_number']
            for p in related_pickings - without_tracking:
                p.carrier_tracking_ref += "," + res['tracking_number']
        order_currency = self.sale_id.currency_id or self.company_id.currency_id
        msg = _("Shipment sent to carrier %(carrier_name)s for shipping with tracking number %(ref)s",
                carrier_name=self.carrier_id.name,
                ref=self.carrier_tracking_ref) + \
              Markup("<br/>") + \
              _("Cost: %(price).2f %(currency)s",
                price=self.carrier_price,
                currency=order_currency.name)
        self.message_post(body=msg)
        self._add_delivery_cost_to_so()

    def _check_carrier_details_compliance(self):
        """Hook to check if a delivery is compliant in regard of the carrier.
        """
        return

    def print_return_label(self):
        self.ensure_one()
        self.carrier_id.get_return_label(self)

    def _get_matching_delivery_lines(self):
        return self.sale_id.order_line.filtered(
            lambda l: l.is_delivery
            and l.currency_id.is_zero(l.price_unit)
            and l.product_id == self.carrier_id.product_id
        )

    def _prepare_sale_delivery_line_vals(self):
        return {
            'price_unit': self.carrier_price,
            # remove the estimated price from the description
            'name': self.carrier_id.with_context(lang=self.partner_id.lang).name,
        }

    def _add_delivery_cost_to_so(self):
        self.ensure_one()
        sale_order = self.sale_id
        if sale_order and self.carrier_id.invoice_policy == 'real' and self.carrier_price:
            delivery_lines = self._get_matching_delivery_lines()
            if not delivery_lines:
                delivery_lines = sale_order._create_delivery_line(self.carrier_id, self.carrier_price)
            vals = self._prepare_sale_delivery_line_vals()
            delivery_lines[0].write(vals)

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
            msg = _("Tracking links for shipment:") + Markup("<br/>")
            for tracker in carrier_trackers:
                msg += Markup('<a href="%s">%s</a><br/>') % (tracker[1], tracker[0])
            self.message_post(body=msg)
            return self.env["ir.actions.actions"]._for_xml_id("stock_delivery.act_delivery_trackers_url")

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

    def _get_estimated_weight(self):
        self.ensure_one()
        weight = 0.0
        for move in self.move_ids:
            weight += move.product_qty * move.product_id.weight
        return weight

    def _should_generate_commercial_invoice(self):
        self.ensure_one()
        return self.picking_type_id.warehouse_id.partner_id.country_id != self.partner_id.country_id
