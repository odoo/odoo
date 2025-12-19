from odoo import _, models
from odoo.exceptions import UserError


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _compute_sending_method_checkboxes(self):
        """ EXTENDS 'account'
        If Customer is not valid on PDP, we disable the checkbox. Also add the proxy mode if not in prod.
        """
        for wizard in self:
            pdp_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
            pdp_partner.button_pdp_check_partner_endpoint(company=wizard.company_id)
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            pdp_checkbox = wizard.sending_method_checkboxes.get('pdp')
            if not pdp_checkbox:
                continue

            pdp_partner = wizard.move_id.partner_id.commercial_partner_id.with_company(wizard.company_id)
            pdp_proxy_mode = wizard.company_id._get_pdp_edi_mode()
            partner_is_valid = pdp_partner.pdp_verification_state == 'valid'
            verification_display_state_map = dict(pdp_partner._fields['pdp_verification_display_state']._description_selection(self.env))
            addendum_disable_reason = "" if partner_is_valid else f" ({verification_display_state_map[pdp_partner.pdp_verification_display_state]})"
            vals_not_valid = {'readonly': True, 'checked': False} if addendum_disable_reason else {}
            addendum_mode = ''
            if pdp_proxy_mode == 'test':
                addendum_mode = _(' (Test)')
            elif pdp_proxy_mode == 'demo':
                addendum_mode = _(' (Demo)')
            if addendum_disable_reason or addendum_mode:
                wizard.sending_method_checkboxes = {
                    **wizard.sending_method_checkboxes,
                    'pdp': {
                        **pdp_checkbox,
                        **vals_not_valid,
                        'label': f"{pdp_checkbox['label']}{addendum_disable_reason}{addendum_mode}",
                    },
                }

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.sending_methods and 'pdp' in self.sending_methods:
            move = self.move_id.with_company(self.move_id.company_id)
            if move.partner_id.commercial_partner_id.pdp_verification_state != 'valid':
                raise UserError(_("Partner doesn't have a valid PDP configuration."))

            move.pdp_move_state = 'to_send'
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
