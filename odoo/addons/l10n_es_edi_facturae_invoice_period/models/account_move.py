from odoo import fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_invoicing_period_start_date = fields.Date(string="Invoice Period Start Date")
    l10n_es_invoicing_period_end_date = fields.Date(string="Invoice Period End Date")

    def _l10n_es_edi_facturae_export_facturae(self):
        # EXTENDS l10n_es_edi_facturae
        template_values, signature_values = super()._l10n_es_edi_facturae_export_facturae()

        invoicing_period = {
            'StartDate': self.l10n_es_invoicing_period_start_date,
            'EndDate': self.l10n_es_invoicing_period_end_date,
        } if self.l10n_es_invoicing_period_start_date and self.l10n_es_invoicing_period_end_date else None

        template_values['Invoices'][0]['InvoiceIssueData']['InvoicingPeriod'] = invoicing_period
        return template_values, signature_values
