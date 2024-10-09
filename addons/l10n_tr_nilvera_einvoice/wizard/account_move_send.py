from io import BytesIO
import logging

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_tr_nilvera_einvoice_enable_xml = fields.Boolean(compute='_compute_l10n_tr_nilvera_einvoice_enable_xml')
    l10n_tr_nilvera_einvoice_checkbox_xml = fields.Boolean(
        string="Send E-Invoice to Nilvera",
        default=True,
        company_dependent=True,
    )
    l10n_tr_nilvera_warnings = fields.Json(compute='_compute_l10n_tr_nilvera_warnings')

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_tr_nilvera_einvoice_xml'] = self.l10n_tr_nilvera_einvoice_checkbox_xml
        return values

    @api.model
    def _get_wizard_vals_restrict_to(self, only_options):
        # EXTENDS 'account'
        values = super()._get_wizard_vals_restrict_to(only_options)
        return {
            'l10n_tr_nilvera_einvoice_checkbox_xml': False,
            **values,
        }

    @api.model
    def _get_default_l10n_tr_nilvera_einvoice_enable_einvoice(self, move):
        return (
            not move.invoice_pdf_report_id \
            and not move.l10n_tr_nilvera_einvoice_xml_id \
            and move.is_invoice(include_receipts=True) \
            and move.company_id.country_code == 'TR' \
            # and invoice not sent before
        )

    def _l10n_tr_nilvera_check_invoices(self):
        self.move_ids._l10n_tr_nilvera_get_documents()
        moves_to_check = self.move_ids.filtered(self._get_default_l10n_tr_nilvera_einvoice_enable_einvoice)
        invalid_records = moves_to_check.partner_id.filtered(
            lambda p: p.country_code != 'TR' or not p.city or not p.state_id
        )
        if invalid_records:
            return {
                "partner_data_missing": {
                    "message": _("The following partner(s) are either not Turkish or are missing the city and/or the state fields."),
                    "action_text": _("View Partner(s)"),
                    "action": invalid_records._get_records_action(
                        name=_("Check data on Partner(s)")
                    ),
                }
            }

        return {}

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_l10n_tr_nilvera_einvoice_enable_xml(self):
        for wizard in self:
            wizard.l10n_tr_nilvera_einvoice_enable_xml = any(self._get_default_l10n_tr_nilvera_einvoice_enable_einvoice(move) for move in wizard.move_ids)

    @api.depends('l10n_tr_nilvera_einvoice_enable_xml')
    def _compute_l10n_tr_nilvera_einvoice_checkbox_xml(self):
        for wizard in self:
            wizard.l10n_tr_nilvera_einvoice_checkbox_xml = wizard.l10n_tr_nilvera_einvoice_enable_xml

    @api.depends('l10n_tr_nilvera_einvoice_checkbox_xml')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.depends('l10n_tr_nilvera_einvoice_checkbox_xml')
    def _compute_l10n_tr_nilvera_warnings(self):
        for wizard in self:
            if wizard.l10n_tr_nilvera_einvoice_checkbox_xml:
                wizard.l10n_tr_nilvera_warnings = wizard._l10n_tr_nilvera_check_invoices()
            else:
                wizard.l10n_tr_nilvera_warnings = False

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_tr_nilvera_einvoice_xml_id

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if invoice_data.get('l10n_tr_nilvera_einvoice_xml') and self._get_default_l10n_tr_nilvera_einvoice_enable_einvoice(invoice):
            try:
                builder = self.env['account.edi.xml.ubl.tr']
                xml_content, errors = builder._export_invoice(invoice)
                if errors:
                    invoice_data['error'] = {
                        'error_title': _("Errors occurred while creating the EDI document (format: %s):", "E-Invoice"),
                        'errors': errors,
                    }
                else:
                    invoice_data['l10n_tr_nilvera_einvoice_attachment_values'] = {
                        'name': invoice._l10n_tr_nilvera_einvoice_get_filename(),
                        'raw': xml_content,
                        'mimetype': 'application/xml',
                        'res_model': invoice._name,
                        'res_id': invoice.id,
                        'res_field': 'l10n_tr_nilvera_einvoice_xml_file',  # Binary field
                    }
            except UserError as e:
                if self.env.context.get('forced_invoice'):
                    _logger.warning(
                        'An error occured during generation of E-Invoice EDI of %s: %s',
                        invoice.name,
                        e.args[0]
                    )
                else:
                    raise

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():
            attachment_values = invoice_data.get('l10n_tr_nilvera_einvoice_attachment_values')
            xml_file = BytesIO(attachment_values.get('raw'))
            xml_file.name = attachment_values.get('name')

            if not invoice.partner_id.l10n_tr_nilvera_customer_alias_id:
                # If no alias is saved, the user is either an E-Archive user or we haven't checked before. Check again
                # just in case.
                invoice.partner_id.check_nilvera_customer()
            customer_alias = invoice.partner_id.l10n_tr_nilvera_customer_alias_id.name
            if customer_alias:  # E-Invoice
                invoice._l10n_tr_nilvera_submit_einvoice(xml_file, customer_alias)
            else:   # E-Archive
                invoice._l10n_tr_nilvera_submit_earchive(xml_file)

    @api.model
    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)

        attachment_vals = invoice_data.get('l10n_tr_nilvera_einvoice_attachment_values')
        if attachment_vals:
            self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_vals)
            invoice.invalidate_recordset(fnames=['l10n_tr_nilvera_einvoice_xml_id', 'l10n_tr_nilvera_einvoice_xml_file'])
