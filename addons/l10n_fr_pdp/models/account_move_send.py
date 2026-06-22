from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_sending_methods(self, move) -> str:
        # EXTENDS 'account_peppol' to not select Peppol / PDP for B2C invoices
        partner = move.commercial_partner_id.with_company(move.company_id)
        if move.company_id._get_peppol_proxy_type() != 'pdp' or not partner._l10n_fr_pdp_is_b2c():
            return super()._get_default_sending_methods(move)
        return {'email'}

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
        if edi_user.proxy_type == 'pdp':
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
        if relevant_moves.company_id.filtered(lambda c: c._peppol_is_french_company()):
            alert['action'].update({
                'tag': 'l10n_fr_pdp.what_is_pdp',
                'name': self.env._("Why should I use E-Invoicing?"),
            })
            alert['action_text'] = self.env._("Why should you use it ?")
        return alert

    def _get_peppol_what_is_peppol_message(self, companies, moves, relevant_moves):
        if relevant_moves.company_id.filtered(lambda c: c._peppol_is_french_company()):
            return self.env._("You can send this invoice electronically via Approved Platform.")
        return super()._get_peppol_what_is_peppol_message(companies, moves, relevant_moves)

    def _get_peppol_partner_want_peppol_message(self, partners, relevant_moves):
        french_regulated_moves = relevant_moves.filtered(
            lambda m: (
                m.company_id._peppol_is_french_company()
                and m.partner_id.commercial_partner_id.with_company(self.company_id)._get_pdp_receiver_identification_info()[0] == 'pdp'
            )
        )
        if french_regulated_moves:
            return self.env._("%s has requested electronic invoices reception via French E-Invoicing.", partners.display_name)
        return super()._get_peppol_partner_want_peppol_message(partners, relevant_moves)

    def _get_peppol_what_is_pdp_message(self, companies, moves, relevant_moves):
        return self.env._("Consider registering to use the Approved Platform for French E-Invoicing")

    def action_what_is_peppol_activate(self, moves):
        companies = moves.company_id
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        if (
            len(companies) == 1
            and companies._peppol_is_french_company()
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
