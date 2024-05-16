# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Product(models.Model):
    _inherit = 'product.product'

    event_ticket_ids = fields.One2many('event.event.ticket', 'product_id', string='Event Tickets')
    is_event_ticket = fields.Boolean(
        compute="_compute_is_event_ticket",
        compute_sudo=True,
        search="_search_is_event_ticket",
    )

    def _compute_is_event_ticket(self):
        has_event_ticket_per_product = {
            product.id: bool(count)
            for product, count in self.env['event.event.ticket']._read_group(
                domain=[('product_id', 'in', self.ids)],
                groupby=['product_id'],
                aggregates=['__count'],
            )
        }
        for product in self:
            product.is_event_ticket = has_event_ticket_per_product.get(product.id, False)

    def _search_is_event_ticket(self, operator, value):
        EventTicket = self.env['event.event.ticket']
        subquery = EventTicket.sudo()._search([('product_id', '!=', False)])
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'inselect'
        else:
            search_operator = 'not inselect'

        return [
            ('id', search_operator, subquery.select('"%s"."product_id"' % EventTicket._table)
        )]
