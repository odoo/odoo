from odoo import api, fields, models


class Product(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')
    is_event_ticket = fields.Boolean(compute="_compute_is_event_ticket")

    def _compute_is_event_ticket(self):
        has_event_ticket_per_product = {
            product.id: bool(count)
            for product, count in self.env['event.event.ticket']._read_group(
                domain=[
                    ('product_id', '!=', False),
                    ('event_id.date_end', '>=', fields.date.today()),
                ],
                groupby=['product_id'],
                aggregates=['__count'],
            )
        }
        for product in self:
            product.is_event_ticket = has_event_ticket_per_product.get(product.id, False)
