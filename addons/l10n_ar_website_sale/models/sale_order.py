import pytz

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        """ Necessary because if someone creates an invoice after 9 pm Argentina time, if the invoice is created
        automatically, then it is created with the date of the next day (UTC date) instead of today.

        This fix is necessary because it causes problems validating invoices in ARCA (ex AFIP), since when generating
        the invoice with the date of the next day, no more invoices could be generated with today's date.

        We took the same approach that was used in the POS module to set the date, in this case always forcing the
        Argentina timezone """
        res = super()._prepare_invoice()

        # Find the invoice journal (given, or default one)
        journal_id = res.get('journal_id')
        journal = self.env['account.journal'].browse(journal_id) if journal_id else \
            self.env['account.journal'].search([('type', '=', 'sale')], limit=1)

        if journal.country_code == 'AR':
            timezone = pytz.timezone('America/Buenos_Aires')
            context_today_ar = fields.Datetime.now().astimezone(timezone).date()
            res.update({'invoice_date': context_today_ar})

        return res
