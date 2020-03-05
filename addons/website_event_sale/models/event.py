from odoo import api, fields, models

class EventTemplateTicket(models.Model):
    _inherit = 'event.event.ticket'

    price_reduce = fields.Float(string="Price Reduce", compute="_compute_price_reduce", digits='Product Price')

    @api.depends('product_id')
    def _compute_price_reduce(self):
        for record in self:
            product = record.product_id
            discount = product.lst_price and (product.lst_price - product.price) / product.lst_price or 0.0
            record.price_reduce = (1.0 - discount) * record.price

    price_reduce_taxinc = fields.Float(string='Price Reduce Tax inc', compute='_compute_price_reduce_taxinc')

    def _compute_price_reduce_taxinc(self):
        for record in self:
            # sudo necessary here since the field is most probably accessed through the website
            tax_ids = record.sudo().product_id.taxes_id.filtered(lambda r: r.company_id == record.event_id.company_id)
            taxes = tax_ids.compute_all(record.price_reduce, record.event_id.company_id.currency_id, 1.0, product=record.product_id)
            record.price_reduce_taxinc = taxes['total_included']
