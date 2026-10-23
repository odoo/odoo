from datetime import datetime

from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05]
        result = super()._get_exchanged_document_vals(invoice)

        result['included_note_list'].extend([
            {
                'subject_code': code,
                'content': content,
            } for code, content in invoice._l10n_fr_pdp_get_default_notes().items()
        ])

        return result

    def _get_import_document_amount_sign(self, tree):
        type_code = tree.findtext('.//{*}ExchangedDocument/{*}TypeCode')
        if type_code == '262':
            # The generic Factur-X importer only recognizes 381 and 261 as credit notes.
            return 'refund', 1
        return super()._get_import_document_amount_sign(tree)

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        logs = super()._import_fill_invoice_form(invoice, tree, qty_factor)
        document_type_code = tree.findtext('./{*}ExchangedDocument/{*}TypeCode')

        invoice._l10n_fr_pdp_set_studio_field_value(
            'x_studio_peppol_contract_document_reference_id',
            {'char', 'text'},
            tree.findtext(
                './{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeAgreement/'
                '{*}ContractReferencedDocument/{*}IssuerAssignedID'
            ),
        )
        period_path = (
            './{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/'
            '{*}BillingSpecifiedPeriod'
        )
        self._l10n_fr_pdp_set_facturx_date(
            invoice,
            'x_studio_peppol_invoice_period_start_date',
            tree.findtext(f'{period_path}/{{*}}StartDateTime/{{*}}DateTimeString'),
        )
        self._l10n_fr_pdp_set_facturx_date(
            invoice,
            'x_studio_peppol_invoice_period_end_date',
            tree.findtext(f'{period_path}/{{*}}EndDateTime/{{*}}DateTimeString'),
        )

        if document_type_code == '381':
            reference_path = (
                './{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/'
                '{*}InvoiceReferencedDocument'
            )
            invoice._l10n_fr_pdp_set_studio_field_value(
                'x_studio_peppol_contract_document_reference_id',
                {'char', 'text'},
                tree.findtext(f'{reference_path}/{{*}}IssuerAssignedID'),
            )
            self._l10n_fr_pdp_set_facturx_date(
                invoice,
                'x_studio_peppol_invoice_previous_date',
                tree.findtext(f'{reference_path}/{{*}}FormattedIssueDateTime/{{*}}DateTimeString'),
            )

        return logs

    def _l10n_fr_pdp_set_facturx_date(self, invoice, field_name, value):
        if value:
            invoice._l10n_fr_pdp_set_studio_field_value(
                field_name,
                {'date'},
                datetime.strptime(value.strip(), '%Y%m%d').date(),
            )
