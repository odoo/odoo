# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, models, fields, api, tools
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import SQL

# Time during which an online payment in progress holds the slot of its self order
PENDING_ONLINE_PAYMENT_HOLD_MINUTES = 10


class PresetSlotUnavailableError(ValidationError):
    """ The timing slot of the order is already passed or full, another one must be selected. """


class PosOrder(models.Model):
    _inherit = 'pos.order'

    use_self_order_online_payment = fields.Boolean(compute='_compute_use_self_order_online_payment', store=True, readonly=True)

    def get_order_to_print(self):
        self.ensure_one()

        if self.nb_print > 0:
            raise ValueError("This order has already been printed automatically.")

        self.nb_print += 1
        return self.read_pos_data([], self.config_id.id)

    @api.depends('config_id.self_order_online_payment_method_id')
    def _compute_use_self_order_online_payment(self):
        for order in self:
            order.use_self_order_online_payment = bool(order.config_id.self_order_online_payment_method_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'use_self_order_online_payment' not in vals or vals['use_self_order_online_payment']:
                session = self.env['pos.session'].browse(vals['session_id'])
                config = session.config_id
                vals['use_self_order_online_payment'] = bool(config.self_order_online_payment_method_id)
        return super().create(vals_list)

    def write(self, vals):
        # Because use_self_order_online_payment is not intended to be changed manually,
        # avoid to raise an error.
        if 'use_self_order_online_payment' not in vals:
            return super().write(vals)

        can_change_self_order_domain = [('state', '=', 'draft')]
        if vals['use_self_order_online_payment']:
            can_change_self_order_domain += [('config_id.self_order_online_payment_method_id', '!=', False)]

        can_change_self_order_orders = self.filtered_domain(can_change_self_order_domain)
        cannot_change_self_order_orders = self - can_change_self_order_orders

        res = True
        if can_change_self_order_orders:
            res = super(PosOrder, can_change_self_order_orders).write(vals) and res
        if cannot_change_self_order_orders:
            clean_vals = vals.copy()
            clean_vals.pop('use_self_order_online_payment', None)
            res = super(PosOrder, cannot_change_self_order_orders).write(clean_vals) and res

        return res

    @api.depends('use_self_order_online_payment', 'config_id.self_order_online_payment_method_id', 'config_id.payment_method_ids')
    def _compute_online_payment_method_id(self):
        for order in self:
            if order.use_self_order_online_payment:
                # It is expected to use the self order online payment method.
                # If for any reason it is not defined, then the online payment
                # of the order is set to null to make the problem noticeable.
                order.online_payment_method_id = order.config_id.self_order_online_payment_method_id
            else:
                super(PosOrder, order)._compute_online_payment_method_id()

    def get_and_set_online_payments_data(self, next_online_payment_amount=False):
        res = super().get_and_set_online_payments_data(next_online_payment_amount)
        if 'paid_order' not in res and not res.get('deleted', False) and not isinstance(next_online_payment_amount, bool):
            # This method is only called in the POS frontend flow, not self order.
            # If the next online payment is 0, then the online payment of the frontend
            # flow is cancelled, and the default flow is self order if it is configured.
            self.use_self_order_online_payment = tools.float_is_zero(next_online_payment_amount, precision_rounding=self.currency_id.rounding) and self.config_id.self_order_online_payment_method_id
        return res

    def _send_notification_online_payment_status(self, status):
        if status == 'success':
            self._send_order()

        self.config_id._notify("ONLINE_PAYMENT_STATUS", {
            'status': status,  # progress, success, fail
            'order_id': self.id,
        })

    def _load_pos_self_data_fields(self, config):
        result = super()._load_pos_self_data_fields(config)
        return result + ['online_payment_method_id', 'next_online_payment_amount']

    @api.model
    def _check_pos_order(self, pos_config, order, device_type, table=None):
        data = super()._check_pos_order(pos_config, order, device_type, table)
        data['use_self_order_online_payment'] = order.get('use_self_order_online_payment')
        return data

    @api.model
    def _get_pending_online_payment_domain(self):
        """ Draft mobile self orders waiting for their online payment (pay after each order). """
        return Domain([
            ('state', '=', 'draft'),
            ('source', '=', 'mobile'),
            ('use_self_order_online_payment', '=', True),
            ('config_id.self_ordering_pay_after', '=', 'each'),
            ('amount_total', '>', 0),
        ])

    @api.model
    def _get_payment_in_progress_domain(self):
        """ Orders with an online payment started a few minutes ago and not finished yet,
        or with an online payment accepted by the provider but not processed yet on the order.
        """
        cutoff = fields.Datetime.now() - timedelta(minutes=PENDING_ONLINE_PAYMENT_HOLD_MINUTES)
        transactions_query = self.env['payment.transaction'].sudo()._search(
            Domain('pos_order_id', '!=', False)
            & (
                Domain('state', 'in', ('authorized', 'done'))
                | (Domain('state', 'in', ('draft', 'pending')) & Domain('create_date', '>=', cutoff))
            )
        )
        return Domain('id', 'in', transactions_query.subselect(SQL('pos_order_id')))

    @api.model
    def _get_online_payment_not_holding_slot_domain(self):
        """ Orders waiting for their online payment that do not hold their slot. """
        return Domain.AND([self._get_pending_online_payment_domain(), ~self._get_payment_in_progress_domain()])

    def _check_preset_slot_availability(self):
        """ Raise if the timing slot of the order is already in the past or full with other orders. """
        self.ensure_one()
        preset = self.preset_id
        # Only an order waiting for its online payment can lose its slot
        if not preset.use_timing or not self.preset_time or not self.filtered_domain(self._get_pending_online_payment_domain()):
            return

        # Slot is in the past
        if self.preset_time < fields.Datetime.now():
            raise PresetSlotUnavailableError(_("This timing slot is already passed, please select another one."))

        # Slot is full with other orders: paid ones, ones with a payment in progress, or with nothing to pay online
        other_orders_count = self.env['pos.order'].search_count(Domain.AND([
            preset._get_slots_usage_domain(),
            [('preset_time', '=', self.preset_time), ('id', '!=', self.id)],
        ]))
        if other_orders_count >= preset.slots_per_interval:
            raise PresetSlotUnavailableError(_("Full capacity reached for this timing slot, please select another one."))
