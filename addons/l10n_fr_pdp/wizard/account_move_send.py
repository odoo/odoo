from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    company_on_pdp = fields.Boolean(compute='_compute_company_on_pdp')

    @api.depends('company_id')
    def _compute_company_on_pdp(self):
        for wizard in self:
            wizard.company_on_pdp = wizard.company_id._get_peppol_proxy_type() == 'pdp'

    def _get_invalid_peppol_partners(self):
        partners = super()._get_invalid_peppol_partners()
        if not self.company_on_pdp:
            return partners
        return partners.filtered(lambda partner: partner._get_pdp_receiver_identification_info()[0] != 'pdp')

    @api.depends('company_on_pdp')
    def _compute_peppol_warning(self):
        super()._compute_peppol_warning()
        for wizard in self:
            if not wizard.company_on_pdp:
                continue

            invalid_pdp_partners = super()._get_invalid_peppol_partners().filtered(
                lambda partner: partner._get_pdp_receiver_identification_info()[0] == 'pdp'
            )
            if invalid_pdp_partners:
                names = ', '.join(invalid_pdp_partners[:5].mapped('display_name'))
                invalid_pdp_partner_warning = _(
                    "The following partners are not registered on the annuaire. "
                    "Please check and verify their E-invoicing endpoint and the Electronic Invoicing format: %s",
                    names,
                )
                wizard.peppol_warning = (wizard.peppol_warning + '\n' if wizard.peppol_warning else '') + invalid_pdp_partner_warning

            wrong_format_pdp_partners = wizard.move_ids.partner_id.commercial_partner_id.filtered(
                lambda partner: (
                    partner.account_peppol_is_endpoint_valid
                    and partner._get_pdp_receiver_identification_info()[0] == 'pdp'
                    and partner.ubl_cii_format != 'ubl_21_fr'
                )
            )
            if wrong_format_pdp_partners:
                names = ', '.join(wrong_format_pdp_partners[:5].mapped('display_name'))
                ubl_21_fr_string = _("France E-Invoicing (UBL 2.1)")
                new_warning = _("For French regulated invoices, only the format '%(format_name)s' is supported."
                                "Please check the following partners: %(partner_names)s",
                                format_name=ubl_21_fr_string, partner_names=names)
                wizard.peppol_warning = (wizard.peppol_warning + '\n' if wizard.peppol_warning else '') + new_warning

    def _get_peppol_document_params(self, partner, invoice, invoice_data):
        edi_user, document = super()._get_peppol_document_params(partner, invoice, invoice_data)
        if edi_user and document and edi_user.proxy_type == 'pdp':
            document.update({
                'flow_number': 2,
                'force_peppol_only': not invoice.company_id.l10n_fr_pdp_send_to_ppf,
            })
        return edi_user, document

    def _get_peppol_attachments_linked_message(self, edi_user):
        if edi_user.proxy_type == 'pdp':
            return _("The invoice has been sent to the Approved Platform. The following attachments were sent with the XML:")
        return super()._get_peppol_attachments_linked_message(edi_user)
