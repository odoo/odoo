from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.sale.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):

    def _create_transaction(self, *args, **kwargs):
        """ Override to create a validation check."""

        tx_sudo = super()._create_transaction(
            *args, **kwargs
        )

        for sale_order in tx_sudo.sale_order_ids:
            company_code = sale_order.company_id.account_fiscal_country_id.code
            gst_treatment = ("regular", "composition", "overseas", "special_economic_zone", "deemed_export")
            if company_code == "IN" and sale_order.partner_id.l10n_in_gst_treatment in gst_treatment:
                invoice_journal = self.env['account.journal'].sudo().search([('type', '=', 'sale'), ('company_id', '=', sale_order.company_id.id)], limit=1)
                for edi_format in invoice_journal.edi_format_ids:
                    if edi_format.code == 'in_einvoice_1_03':
                        errors = edi_format._l10n_in_validate_partner(sale_order.partner_invoice_id)
                        if errors:
                            raise ValidationError(_("Invalid details:\n\n%s", '\n'.join(errors)))
        return tx_sudo
