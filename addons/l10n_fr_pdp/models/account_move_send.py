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
