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

    delivery_method = fields.Selection([
        ('pickup_index', 'Se retira en INDEX TECHNOLOGY'),
        ('delivery_address', 'Se entrega en Dirección de entrega'),
        ('freight_buyer', 'Se entrega en expreso a cargo del comprador'),
    ], string="Forma de entrega")


    sale_condition = fields.Selection([
        ('transfer', 'Transferencia'),
        ('30_day_check', 'Cheque a 30 días'),
        ('60_day_check', 'Cheque a 30 / 60 días'),
        ('90_day_check', 'Cheque a 30 / 60 / 90 días')
    ], string="Condición de venta")

    discount = fields.Float(string="Descuento (%)", default=0.0)

    def _notify_get_email_layout_xmlid(self, message_type=None, subtype_xmlid=None, internal=False):
        return 'sale_extension.custom_mail_notification_layout'

    def print_quotation_report(self):
        return self.env.ref('sale.action_report_saleorder').report_action(self)

    def print_ordernote_report(self):
         return self.env.ref('sale_extension.order_note_pdf').report_action(self)

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

    @api.model
    def create(self, vals):

        order_date = vals.get('date_order')
        date = fields.Datetime.to_datetime(order_date) or fields.Datetime.now()

        domain = [('name', 'like', f"{date.year}-{date.month:02d}-")]
        last_order = self.search(domain, order='id desc', limit=1)
        if last_order and last_order.name:
            last_seq = int(last_order.name.split('-')[-1])
        else:
            last_seq = 0

        new_number = f"{date.year}-{date.month:02d}-{last_seq + 1}"
        vals['name'] = new_number

        return super().create(vals)

    @api.depends('delivery_date')
    def _inverse_delivery_date(self):
        pass

    @api.model
    def action_import_csv(self):
        return {
        }