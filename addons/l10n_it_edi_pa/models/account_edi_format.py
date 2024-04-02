# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_it_edi_check_ordinary_invoice_configuration(self, invoice):
        errors = super()._l10n_it_edi_check_ordinary_invoice_configuration(invoice)
        if invoice._is_commercial_partner_pa():
            if not invoice.l10n_it_origin_document_type:
                errors.append(_("This invoice targets the Public Administration, please fill out"
                              " Origin Document Type field in the Electronic Invoicing tab."))
            if invoice.l10n_it_origin_document_date and invoice.l10n_it_origin_document_date > fields.Date.today():
                errors.append(_("The Origin Document Date cannot be in the future."))
        return errors
