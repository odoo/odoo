import pytz

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_invoices(self, grouped=False, final=False, date=None):
        """ EXTENDS 'sale'
        Necessary because if someone creates an invoice after 9 pm Argentina time, if the invoice is created
        automatically, then it is created with the date of the next day (UTC date) instead of today.

        This fix is necessary because it causes problems validating invoices in ARCA (ex AFIP), since when generating
        the invoice with the date of the next day, no more invoices could be generated with today's date.

        We took the same approach that was used in the POS module to set the date, in this case always forcing the
        Argentina timezone """
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        for invoice in invoices:
            if invoice.country_code == 'AR':
                timezone = pytz.timezone('America/Buenos_Aires')
                context_today_ar = fields.Datetime.now().astimezone(timezone).date()
                invoice.invoice_date = context_today_ar
        return invoices
