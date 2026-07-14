from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

DELIVERY_WEEKDAYS = {0, 2, 4}  # lunes, miercoles, viernes (Python: lunes=0)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.constrains('commitment_date')
    def _check_commitment_date_is_delivery_day(self):
        for order in self:
            if not order.commitment_date:
                continue
            local_dt = fields.Datetime.context_timestamp(order, order.commitment_date)
            if local_dt.weekday() not in DELIVERY_WEEKDAYS:
                raise ValidationError(_(
                    "La fecha de entrega debe ser lunes, miércoles o viernes"
                    " (recibido: %(date)s, %(weekday)s).",
                    date=local_dt.strftime('%Y-%m-%d %H:%M'),
                    weekday=local_dt.strftime('%A'),
                ))
