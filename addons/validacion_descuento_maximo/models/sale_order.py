from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


REVIEW_STATE = 'requires_review'
DISCOUNT_LIMIT_FIELD = 'descuento_maximo_permitido'
DEFAULT_DISCOUNT_LIMIT = 15.0
DISCOUNT_SUPERVISOR_GROUP = 'validacion_descuento_maximo.group_discount_supervisor'
SKIP_DISCOUNT_LIMIT_VALIDATION = 'skip_discount_limit_validation'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    descuento_maximo_permitido = fields.Float(
        string='Descuento Máximo Permisible (%)',
        default=DEFAULT_DISCOUNT_LIMIT
    )
    discount_exceeds_limit = fields.Boolean(
        string='Excede el descuento máximo',
        compute='_compute_discount_exceeds_limit',
    )

    state = fields.Selection(
        selection_add=[(REVIEW_STATE, 'Requiere Revisión')],
        ondelete={REVIEW_STATE: 'set default'}
    )

    def _has_discount_above_limit(self):
        self.ensure_one()
        return any(
            line.discount > self.descuento_maximo_permitido
            for line in self.order_line
            if not line.display_type
        )

    @api.depends('descuento_maximo_permitido', 'order_line.discount', 'order_line.display_type')
    def _compute_discount_exceeds_limit(self):
        for order in self:
            order.discount_exceeds_limit = order._has_discount_above_limit()

    def _send_to_discount_review_if_needed(self):
        orders_to_review = self.filtered('discount_exceeds_limit')
        if orders_to_review:
            orders_to_review.with_context(**{SKIP_DISCOUNT_LIMIT_VALIDATION: True}).write({
                'state': REVIEW_STATE,
            })
        return orders_to_review

    def _can_manage_discount_limit(self):
        return (
            self.env.is_superuser()
            or self.env.user.has_group(DISCOUNT_SUPERVISOR_GROUP)
        )

    def _check_discount_limit_create_access(self, vals_list):
        if self._can_manage_discount_limit():
            return

        for vals in vals_list:
            if vals.get(DISCOUNT_LIMIT_FIELD, DEFAULT_DISCOUNT_LIMIT) != DEFAULT_DISCOUNT_LIMIT:
                raise UserError(_(
                    "Solo un supervisor de descuentos puede modificar el límite máximo de descuento."
                ))

    def _check_discount_limit_write_access(self, vals):
        if DISCOUNT_LIMIT_FIELD not in vals or self._can_manage_discount_limit():
            return

        new_limit = vals[DISCOUNT_LIMIT_FIELD]
        if all(order.descuento_maximo_permitido == new_limit for order in self):
            return

        raise UserError(_(
            "Solo un supervisor de descuentos puede modificar el límite máximo de descuento."
        ))

    @api.constrains('descuento_maximo_permitido')
    def _check_descuento_maximo_permitido(self):
        for order in self:
            if not 0 <= order.descuento_maximo_permitido <= 100:
                raise ValidationError(_(
                    "El descuento máximo permitido debe estar entre 0% y 100%."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_discount_limit_create_access(vals_list)
        orders = super().create(vals_list)
        if not self.env.context.get(SKIP_DISCOUNT_LIMIT_VALIDATION):
            orders._send_to_discount_review_if_needed()
        return orders

    def write(self, vals):
        self._check_discount_limit_write_access(vals)
        result = super().write(vals)

        if self.env.context.get(SKIP_DISCOUNT_LIMIT_VALIDATION):
            return result

        # Avoid reviewing regular state transitions such as canceling or returning to draft.
        if set(vals) == {'state'} and vals.get('state') != 'sale':
            return result

        self._send_to_discount_review_if_needed()
        return result

    def action_confirm(self):
        if self.env.context.get(SKIP_DISCOUNT_LIMIT_VALIDATION):
            return super().action_confirm()

        orders_to_review = self._send_to_discount_review_if_needed()
        orders_to_confirm = self - orders_to_review
        if orders_to_confirm:
            return super(
                SaleOrder,
                orders_to_confirm.with_context(**{SKIP_DISCOUNT_LIMIT_VALIDATION: True})
            ).action_confirm()
        return True

    def _confirmation_error_message(self):
        self.ensure_one()
        if self.env.context.get(SKIP_DISCOUNT_LIMIT_VALIDATION) and self.state == REVIEW_STATE:
            if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
            ):
                return _(
                    "Some order lines are missing a product, you need to correct "
                    "them before going further."
                )
            return False
        return super()._confirmation_error_message()

    def action_approve_discount(self):
        self.ensure_one()

        if self.state != REVIEW_STATE:
            raise UserError(_("Solo se pueden aprobar pedidos en estado 'Requiere Revisión'."))

        if not self.env.user.has_group(DISCOUNT_SUPERVISOR_GROUP):
            raise UserError(_("No tiene permiso para aprobar este descuento."))

        return self.with_context(**{SKIP_DISCOUNT_LIMIT_VALIDATION: True}).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get(SKIP_DISCOUNT_LIMIT_VALIDATION):
            lines.order_id._send_to_discount_review_if_needed()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get(SKIP_DISCOUNT_LIMIT_VALIDATION):
            self.order_id._send_to_discount_review_if_needed()
        return result
