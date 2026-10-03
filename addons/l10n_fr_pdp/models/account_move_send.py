from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_sending_method(self, move) -> str:
        # EXTENDS 'account_peppol' to not select Peppol / PDP for B2C invoices
        partner = move.commercial_partner_id.with_company(move.company_id)
        if move.company_id._get_peppol_proxy_type() != 'pdp' or not partner._l10n_fr_pdp_is_b2c():
            return super()._get_default_sending_method(move)
        return 'email'

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_default_invoice_edi_format(self, move, **kwargs) -> str:
        # EXTENDS 'account'
        if (
            'peppol' in kwargs.get('sending_methods', [])
            and move.company_id._get_peppol_proxy_type() == 'pdp'
            and move.partner_id._get_pdp_receiver_identification_info()[0] == 'pdp'
        ):
            return 'ubl_21_fr'
        return super()._get_default_invoice_edi_format(move, **kwargs)

    def _is_applicable_to_company(self, method, company):
        # EXTENDS 'account'
        if method == 'peppol' and company._get_peppol_proxy_type() == 'pdp':
            return company.account_peppol_proxy_state == 'receiver'
        return super()._is_applicable_to_company(method, company)

    def _get_peppol_document_params(self, partner, invoice, invoice_data):
        edi_user, document = super()._get_peppol_document_params(partner, invoice, invoice_data)
        if edi_user and edi_user.proxy_type == 'pdp':
            if xml_file := invoice_data.get('ubl_cii_xml_attachment_values'):
                if len(xml_file['raw']) > 10000000:
                    invoice_data['error'] = self.env._("Invoice %s exceeds the size limit of 10 MB to be sent via Approved Platform.", invoice.name)
                    return None, None
            if document:
                document.update({
                    'flow_number': 2,
                    'force_peppol_only': not invoice.company_id.l10n_fr_pdp_send_to_ppf,
                })
        return edi_user, document

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_peppol_what_is_peppol_alert(self, moves, moves_data, relevant_moves):
        alert = super()._get_peppol_what_is_peppol_alert(moves, moves_data, relevant_moves)
        if relevant_moves.company_id.filtered(lambda c: c._l10n_fr_pdp_uses_french_terminology()):
            alert['action'].update({
                'tag': 'l10n_fr_pdp.what_is_pdp',
                'name': self.env._("Why should I use E-Invoicing?"),
            })
            alert['action_text'] = self.env._("Why should you use it ?")
        return alert

    def _get_peppol_what_is_peppol_message(self, companies, moves, relevant_moves):
        if relevant_moves.company_id.filtered(lambda c: c._l10n_fr_pdp_uses_french_terminology()):
            return self.env._("You can send this invoice electronically via the Approved Platform.")
        return super()._get_peppol_what_is_peppol_message(companies, moves, relevant_moves)

    def _get_peppol_partner_want_peppol_message(self, partners, relevant_moves):
        french_relevant_moves = relevant_moves.filtered(
            lambda move: (
                move.company_id._l10n_fr_pdp_uses_french_terminology()
                and move.partner_id.commercial_partner_id in partners
            )
        )
        if french_relevant_moves:
            return self.env._("%s has requested electronic invoices reception via French E-Invoicing.", partners.display_name)
        return super()._get_peppol_partner_want_peppol_message(partners, relevant_moves)

    def _get_peppol_what_is_pdp_message(self, companies, moves, relevant_moves):
        return self.env._("Consider registering to use the Approved Platform for French E-Invoicing")

    def action_what_is_peppol_activate(self, moves):
        companies = moves.company_id
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        if (
            len(companies) == 1
            and companies._l10n_fr_pdp_uses_french_terminology()
            and (companies.account_peppol_proxy_state not in can_send or companies._get_peppol_proxy_type() != 'pdp')
        ):
            config = self.env['res.config.settings'].sudo().create({'company_id': companies.id})
            action = {
                # the js action orm calls the action; we only supply the context; i.e. the config id
                'context': {
                    **self.env.context,
                    'active_model': 'account.move',
                    'active_ids': moves.ids,
                    'dialog_size': 'medium',
                    'res_config_settings_id': config.id,
                }
            }
            return action
        return super().action_what_is_peppol_activate(moves)

    def _get_peppol_attachments_linked_message(self, edi_user):
        if edi_user.proxy_type == 'pdp':
            return self.env._("The invoice has been sent to the Approved Platform. The following attachments were sent with the XML:")
        return super()._get_peppol_attachments_linked_message(edi_user)

    @api.model
    def _l10n_fr_pdp_force_send_einvoicing_enabled(self, move=None):
        if self.env.context.get('l10n_fr_pdp_force_send_einvoicing'):
            return True
        sending_data = move.sending_data if move else False
        return bool(sending_data and sending_data.get('l10n_fr_pdp_force_send_einvoicing'))

    def _l10n_fr_pdp_can_force_send_move(self, move, partner, invoice_edi_format):
        """Buyer is absent from the annuaire but routing data is enough to deposit via the PA."""
        return (
            self._l10n_fr_pdp_force_send_einvoicing_enabled(move)
            and move.company_id._get_peppol_proxy_type() == 'pdp'
            and partner._get_pdp_receiver_identification_info()[0] == 'pdp'
            and partner.peppol_eas == '0225'
            and partner.peppol_verification_state == 'not_valid'
            and not partner._l10n_fr_pdp_is_b2c()
            and partner.peppol_endpoint
            and invoice_edi_format == 'ubl_21_fr'
        )

    def _is_applicable_to_move(self, method, move, **move_data):
        # EXTENDS 'account_peppol'
        if method == 'peppol':
            partner = move.partner_id.commercial_partner_id.with_company(move.company_id)
            invoice_edi_format = move_data.get('invoice_edi_format') or partner._get_peppol_edi_format()
            if self._l10n_fr_pdp_can_force_send_move(move, partner, invoice_edi_format):
                # Do not call the endpoint button: it would store "valid" while the
                # lookup still says the buyer is not in the annuaire.
                return all([
                    self._is_applicable_to_company(method, move.company_id),
                    move.company_id.account_peppol_proxy_state != 'rejected',
                    move._need_ubl_cii_xml(invoice_edi_format) or move.ubl_cii_xml_id and not move.peppol_is_sent,
                ])
        return super()._is_applicable_to_move(method, move, **move_data)

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account_peppol'
        regular = {}
        forced = {}
        for invoice, invoice_data in invoices_data.items():
            partner = invoice.partner_id.commercial_partner_id.with_company(invoice.company_id)
            invoice_edi_format = invoice_data.get('invoice_edi_format') or partner._get_peppol_edi_format()
            if (
                'peppol' in invoice_data.get('sending_methods', ())
                and self._l10n_fr_pdp_can_force_send_move(invoice, partner, invoice_edi_format)
            ):
                forced[invoice] = invoice_data
            else:
                regular[invoice] = invoice_data
        if regular:
            super()._call_web_service_after_invoice_pdf_render(regular)
        if forced:
            forced_send = self.with_context(l10n_fr_pdp_force_send_einvoicing=True)
            super(AccountMoveSend, forced_send)._call_web_service_after_invoice_pdf_render(forced)
