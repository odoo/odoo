from odoo import _, api, models
from odoo.exceptions import ValidationError

DELIVERY_WEEKDAYS = {0, 2, 4}  # lunes, miercoles, viernes (Python: lunes=0)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('commitment_date')
    def _check_commitment_date_is_delivery_day(self):
        for order in self:
            if order.commitment_date and order.commitment_date.weekday() not in DELIVERY_WEEKDAYS:
                raise ValidationError(_(
                    "La fecha de entrega debe ser lunes, miércoles o viernes."
                ))
