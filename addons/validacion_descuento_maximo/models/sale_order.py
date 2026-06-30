from odoo import api, fields, models
from odoo.exceptions import UserError


DISCOUNT_LIMIT_ERROR = (
    "¡Alerta de Control (MVP)! Este pedido supera el 15% de descuento permitido. "
    "El presupuesto ha sido retenido en estado 'Requiere Revisión' para la aprobación de Diego."
)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo personalizado para el 15% del MVP
    descuento_maximo_permitido = fields.Float(
        string='Descuento Máximo Permisible (%)',
        default=15.0
    )

    # Añadimos el nuevo estado "Requiere Revisión" al flujo de ventas nativo
    state = fields.Selection(
        selection_add=[('requires_review', 'Requiere Revisión')],
        ondelete={'requires_review': 'set default'}
    )

    def _has_discount_above_limit(self):
        self.ensure_one()
        return any(
            line.discount > self.descuento_maximo_permitido
            for line in self.order_line
            if not line.display_type
        )

    def _raise_discount_limit_error(self):
        for order in self:
            if order._has_discount_above_limit():
                order.with_context(skip_discount_limit_validation=True).write({
                'state': 'requires_review',
                })
                return False
        return True

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if not self.env.context.get('skip_discount_limit_validation'):
            orders._raise_discount_limit_error()
        return orders

    def write(self, vals):
        result = super().write(vals)

        if self.env.context.get('skip_discount_limit_validation'):
            return result

        #evita revalidar si solo cambia estado
        if set(vals.keys()) == {'state'}:
            return result

        self._raise_discount_limit_error()
        return result

    def action_confirm(self):
        if self._raise_discount_limit_error() is False:
            return True
        return super(SaleOrder, self).action_confirm()
    
    def action_approve_discount(self):
        self.ensure_one()

        if not self.env.user.has_group('validacion_descuento_maximo.group_discount_supervisor'):
            raise UserError("No tiene permiso para aprobar este descuento.")

        self.with_context(skip_discount_limit_validation=True).write({
            'state': 'sale'
        })

        return True

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get('skip_discount_limit_validation'):
            lines.order_id._raise_discount_limit_error()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get('skip_discount_limit_validation'):
            self.order_id._raise_discount_limit_error()
        return result
