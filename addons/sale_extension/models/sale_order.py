from odoo import api, fields, models


class SaleOrder(models.Model):
#custom fields

    _inherit='sale.order'


    delivery_date = fields.Date(
        string="Fecha de entrega",
        compute="_compute_delivery_date",
        store=True,
        readOnly=False,
        inverse="_inverse_delivery_date"
    )


    #custom computes
    @api.depends('order_line.item_delivery_date')
    def _compute_delivery_date(self):
        for order in self:
            try:
                delivery_dates = order.order_line.filtered(lambda l: l.item_delivery_date).mapped('item_delivery_date')
                if delivery_dates:
                    order.delivery_date = max(delivery_dates)
                else:
                    order.delivery_date = False
            except Exception as e:
                    print(e)

    @api.depends('delivery_date')
    def _inverse_delivery_date(self):
        pass