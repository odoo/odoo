# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from markupsafe import Markup
import json

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Domain


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package in self:
            package.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    carrier_price = fields.Float(string="Shipping Cost")
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)
    allowed_carrier_ids = fields.Many2many('delivery.carrier', compute='_compute_allowed_carrier_ids')
    carrier_id = fields.Many2one("delivery.carrier", string="Carrier", domain="[('id', 'in', allowed_carrier_ids)]", check_company=True)
    weight = fields.Float(compute='_cal_weight', digits='Stock Weight', store=True, help="Total weight of the products in the picking.", compute_sudo=True)
    carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
    carrier_tracking_url = fields.Char(string='Tracking URL', compute='_compute_carrier_tracking_url')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)
    is_return_picking = fields.Boolean(compute='_compute_return_picking')
    return_label_ids = fields.One2many('ir.attachment', compute='_compute_return_label')
    destination_country_code = fields.Char(related='partner_id.country_id.code', string="Destination Country")
    integration_level = fields.Selection(related='carrier_id.integration_level')

    @api.depends('partner_id', 'carrier_id.max_weight', 'carrier_id.max_volume', 'carrier_id.must_have_tag_ids', 'carrier_id.excluded_tag_ids', 'move_ids.product_id.product_tag_ids', 'move_ids.product_id.weight', 'move_ids.product_id.volume')
    def _compute_allowed_carrier_ids(self):
        for picking in self:
            carriers = self.env['delivery.carrier'].search(self.env['delivery.carrier']._check_company_domain(picking.company_id))
            picking.allowed_carrier_ids = carriers.available_carriers(picking.partner_id, picking) if picking.partner_id else carriers

    @api.depends('carrier_id', 'carrier_tracking_ref')
    def _compute_carrier_tracking_url(self):
        for picking in self:
            picking.carrier_tracking_url = picking.carrier_id.get_tracking_link(picking) if picking.carrier_id and picking.carrier_tracking_ref else False

    @api.depends('carrier_id', 'move_ids')
    def _compute_return_picking(self):
        for picking in self:
            if picking.carrier_id and picking.carrier_id.can_generate_return:
                picking.is_return_picking = any(m.origin_returned_move_id for m in picking.move_ids)
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

    def _pre_action_done_hook(self):
        # Override to force the collection of payment on the final pickings (dest = customer).
        res = super()._pre_action_done_hook()
        if res is not True:
            return res

        final_pickings = self.filtered_domain(
            Domain('location_dest_id.usage', '=', 'customer')
        ).with_context(
            # Treat picked moves as validated during confirmation to ensure the correct
            # amount on delivery is computed and displayed to the user.
            prevalidated_move_ids=self.move_ids.filtered('picked').ids
        )

        # Avoid loops: action_open_pay_on_delivery_form -> get_next_action -> get_final_action ->
        # button_validate -> _pre_action_done_hook
        orders_to_confirm = (
            final_pickings.sale_id - self.env['pay.on.delivery']._get_confirmed_orders()
        )

        return orders_to_confirm.action_open_pay_on_delivery_form()

    def _action_done(self):
        # Override to finish the payment collection flow after the pickings are actually validated.
        # This ensures that any prior validation (`_pre_action_done_hook`) must pass for the
        # payments to be collected.
        res = super()._action_done()
        if confirmed_pickings := (
            self & self.env['pay.on.delivery']._get_confirmed_orders().picking_ids
        ):
            confirmed_pickings._action_confirm_payment_on_delivery()
        return res

    def button_validate(self):
        res = super().button_validate()
        if res is not True:
            return res
        # FIXME: this won't run if the next action is to print the picking report
        for picking in self:
            # `_get_new_picking_values` is used to propagate the carrier before a picking is created (i.e. carrier is set on an SO).
            # Whereas this case handles the propagation of carrier after the picking validation as the carrier maybe set
            # at later stages as well, specifically at the picking level rather than on the Sales Order.
            # This ensures the behavior is consistent across all scenarios (push + pull, all pull, and all push rules).
            if picking.carrier_id:
                picking._get_next_transfers().filtered(
                    lambda p: not p.carrier_id and any(rule.propagate_carrier for rule in p.move_ids.rule_id)
                ).write({'carrier_id': picking.carrier_id.id, 'carrier_tracking_ref': picking.carrier_tracking_ref})
        return res

    def _action_confirm_payment_on_delivery(self, log_action=True):
        """Confirm the pending payments of the linked sales orders, and log the action.

        :raises UserError: If a picking is not linked to a sale order.
        :raises UserError: If an order doesn't have any payment to confirm.
        :return: The confirmed transactions.
        :rtype: payment.transaction
        """
        if no_sale_order := self.filtered(lambda picking: not picking.sale_id):
            raise UserError(
                self.env._(
                    "No sale order is linked to %(pickings)s.",
                    pickings=", ".join(no_sale_order.mapped('display_name')),
                )
            )

        # Override logging to trace the pickings during which the payment were collected.
        delivered_txs_sudo = self.sale_id._action_confirm_payment_on_delivery(log_action=False)

        if log_action:
            self._log_payment_on_delivery(delivered_txs_sudo)

        return delivered_txs_sudo

    def _log_payment_on_delivery(self, delivered_txs_sudo):
        """Log a message on the pickings and the linked documents of the confirmed transactions with
        a link to the pickings during which the payment was collected."""
        delivered_tx_sudo_by_order = delivered_txs_sudo.grouped('sale_order_ids')
        pickings_by_order = self.grouped('sale_id')
        for order in delivered_tx_sudo_by_order.keys() & pickings_by_order.keys():
            delivered_tx_sudo = delivered_tx_sudo_by_order[order]
            pickings = pickings_by_order[order]

            message = self.env._(
                "A payment of %(amount_on_delivery)s was collected for %(order)s on the"
                " delivery of %(pickings)s.",
                amount_on_delivery=delivered_tx_sudo.currency_id.format(delivered_tx_sudo.amount),
                order=order._get_html_link(),
                pickings=Markup(", ").join(picking._get_html_link() for picking in pickings),
            )

            delivered_tx_sudo._log_message_on_linked_documents(message)
            for picking in pickings:
                picking.message_post(body=message)

    def _carrier_exception_note(self, exception):
        self.ensure_one()
        line_1 = _("Exception occurred with respect to carrier on the transfer")
        line_2 = _("Manual actions might be needed.")
        line_3 = _("Exception:")
        return Markup('<div> {line_1} <a href="#" data-oe-model="stock.picking" data-oe-id="{picking_id}"> {picking_name}</a>. {line_2}<div class="mt16"><p>{line_3} {exception}</p></div></div>').format(line_1=line_1, line_2=line_2, line_3=line_3, picking_id=self.id, picking_name=self.name, exception=exception)

    def _send_confirmation_email(self):
        # The carrier's API processes validity checks and parcels generation one picking at a time.
        # However, since a UserError of any of the picking will cause a rollback of the entire batch
        # on Odoo's side and since pickings that were already processed on the carrier's side must
        # stay validated, UserErrors might need to be replaced by activity warnings.

        processed_carrier_picking = False

        for pick in self:
            try:
                if pick.carrier_id and pick.carrier_id.integration_level == 'rate_and_ship' and pick.picking_type_code != 'incoming' and not pick.carrier_tracking_ref and pick.picking_type_id.print_label:
                    pick.sudo().send_to_shipper()
                pick._check_carrier_details_compliance()
                if pick.carrier_id:
                    processed_carrier_picking = True
            except (UserError) as e:
                if processed_carrier_picking:
                    # We can not raise a UserError at this point
                    exception_message = str(e)
                    pick.message_post(body=exception_message, message_type='notification')
                    pick.sudo().activity_schedule(
                        'mail.mail_activity_data_warning',
                        date.today(),
                        note=pick._carrier_exception_note(exception_message),
                        user_id=pick.user_id.id or self.env.uid,
                        )
                else:
                    raise e

        return super(StockPicking, self)._send_confirmation_email()

    def send_to_shipper(self):
        self.ensure_one()
        res = self.carrier_id.send_shipping(self)[0]
        if self.carrier_id.free_over and self.sale_id:
            amount_without_delivery = self.sale_id._compute_amount_total_without_delivery()
            if self.carrier_id._compute_currency(self.sale_id, amount_without_delivery, 'pricelist_to_company') >= self.carrier_id.amount:
                res['exact_price'] = 0.0
        self.carrier_price = self.carrier_id._apply_margins(res['exact_price'], self.sale_id)
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
