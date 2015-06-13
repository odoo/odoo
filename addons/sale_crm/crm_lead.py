
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp

class crm_lead(models.Model):
    _inherit = ['crm.lead']

    @api.one
    @api.depends('order_ids')
    def _get_sale_amount_total(self):
        total = 0.0
        nbr = 0
        for order in self.order_ids:
            if order.state == 'draft':
                nbr += 1
            if order.state not in ('draft', 'cancel'):
                total += order.currency_id.compute(order.amount_untaxed, self.company_currency)
        self.sale_amount_total = total
        self.sale_number = nbr

    sale_amount_total= fields.Float(compute='_get_sale_amount_total', string="Sum of Orders", readonly=True, digits_compute=dp.get_precision('Account'))
    sale_number = fields.Integer(compute='_get_sale_amount_total', string="Number of Quotations", readonly=True)
    order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders')
