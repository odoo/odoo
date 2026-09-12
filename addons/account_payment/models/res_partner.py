from odoo import fields, models
from odoo.tools import hmac


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_overdue_invoices_token(self):
        self.ensure_one()
        overdue_amount = dict(self.env['account.move']._read_group(
            domain=[
                ('state', 'not in', ('cancel', 'draft')),
                ('move_type', 'in', ('out_invoice', 'out_receipt')),
                ('payment_state', 'not in', ('in_payment', 'paid', 'reversed', 'blocked', 'invoicing_legacy')),
                ('invoice_date_due', '<', fields.Date.today()),
                ('partner_id', '=', self.id),
                ('company_id', 'in', self.env.companies.ids),
            ],
            groupby=['partner_id'],
            aggregates=['amount_total:sum'],
        )).get(self, 0.0)
        return hmac(self.env(su=True), 'account_payment.model_res_partner.overdue_invoices_token', {
            'id': self.id,
            'company_ids': self.env.companies.ids,
            'overdue_amount': self.currency_id.format(overdue_amount),
        })
