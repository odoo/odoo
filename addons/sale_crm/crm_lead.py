
from openerp import models, fields, api, _, tools
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import openerp.addons.decimal_precision as dp

class crm_lead(models.Model):
    _inherit = ['crm.lead']

    @api.one
    @api.depends('order_ids')
    def _get_sale_amount_total(self):
        total = 0.0
        nbr = 0
        for order in self.order_ids:
            if order.state in ('draft', 'sent'):
                nbr += 1
            if order.state not in ('draft', 'sent', 'cancel'):
                total += order.currency_id.compute(order.amount_untaxed, self.company_currency)
        self.sale_amount_total = total
        self.sale_number = nbr

    sale_amount_total= fields.Float(compute='_get_sale_amount_total', string="Sum of Orders", readonly=True, digits=0)
    sale_number = fields.Integer(compute='_get_sale_amount_total', string="Number of Quotations", readonly=True)
    order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders')

    def retrieve_sales_dashboard(self, cr, uid, context=None):
        res = super(crm_lead, self).retrieve_sales_dashboard(cr, uid, context=None)

        res['invoiced'] = {
            'this_month': 0,
            'last_month': 0,
        }
        account_invoice_domain = [
            ('state', 'in', ['open', 'paid']),
            ('user_id', '=', uid),
            ('date', '>=', date.today().replace(day=1) - relativedelta(months=+1)),
            ('type', 'in', ['out_invoice', 'out_refund'])
        ]

        invoice_ids = self.pool.get('account.invoice').search_read(cr, uid, account_invoice_domain, ['date', 'amount_untaxed_signed'], context=context)
        for inv in invoice_ids:
            if inv['date']:
                inv_date = datetime.strptime(inv['date'], tools.DEFAULT_SERVER_DATE_FORMAT).date()
                if inv_date <= date.today() and inv_date >= date.today().replace(day=1):
                    res['invoiced']['this_month'] += inv['amount_untaxed_signed']
                elif inv_date < date.today().replace(day=1) and inv_date >= date.today().replace(day=1) - relativedelta(months=+1):
                    res['invoiced']['last_month'] += inv['amount_untaxed_signed']

        res['invoiced']['target'] = self.pool('res.users').browse(cr, uid, uid, context=context).target_sales_invoiced
        return res
