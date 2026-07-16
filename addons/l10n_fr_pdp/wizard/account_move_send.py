from odoo import _, api, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    def _compute_peppol_warning(self):
        super()._compute_peppol_warning()
        for wizard in self:
            if wizard.company_id._get_peppol_proxy_type() != 'pdp':
                continue
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
