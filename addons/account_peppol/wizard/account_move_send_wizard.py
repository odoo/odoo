# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import AccessError, UserError


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    def _get_peppol_checkbox_label(self, default_label):
        return default_label

    def _get_peppol_checkbox_addendum_disable_reason(self):
        self.ensure_one()
        peppol_partner = self.move_id.partner_id.commercial_partner_id.with_company(self.company_id)
        if not peppol_partner.peppol_eas or not peppol_partner.peppol_endpoint:
            peppol_partner._compute_peppol_endpoint()  # Try to recompute the Peppol credentials.
        eas_label = dict(peppol_partner._fields['peppol_eas']._description_selection(self.env)).get(peppol_partner.peppol_eas)
        if peppol_partner.peppol_verification_state == 'not_valid':
            addendum_disable_reason = _(' (Customer not on Peppol)')
        elif peppol_partner.peppol_verification_state == 'not_verified':
            # The recomputation of the Peppol credentials did not manage to fill these fields.
            addendum_disable_reason = _(' (Customer not on Peppol)')
            if not peppol_partner.peppol_eas or not peppol_partner.peppol_endpoint:
                if not peppol_partner.vat:
                    addendum_disable_reason = _(' (no VAT)')
                elif eas_label:
                    addendum_disable_reason = _(
                        ' (Missing %(eas)s)',
                        eas=eas_label,
                    )
        elif self.company_id._have_unauthorized_peppol_parent_company():
            addendum_disable_reason = _(' (no access)')
        else:
            addendum_disable_reason = ''
        return addendum_disable_reason

    def _compute_sending_method_checkboxes(self):
        """ EXTENDS 'account'
        If Customer is not valid on Peppol, we disable the checkbox. Also add the proxy mode if not in prod.
        """
        super()._compute_sending_method_checkboxes()
        for wizard in self:
            if peppol_checkbox := wizard.sending_method_checkboxes.get('peppol'):
                peppol_proxy_mode = wizard.company_id._get_peppol_edi_mode()
                peppol_label = wizard._get_peppol_checkbox_label(peppol_checkbox['label'])
                addendum_disable_reason = wizard._get_peppol_checkbox_addendum_disable_reason()
                vals_not_valid = {'readonly': True, 'checked': False} if addendum_disable_reason else {}
                addendum_mode = ''
                if peppol_proxy_mode == 'test':
                    addendum_mode = _(' (Test)')
                elif peppol_proxy_mode == 'demo':
                    addendum_mode = _(' (Demo)')
                if addendum_disable_reason or addendum_mode:
                    wizard.sending_method_checkboxes = {
                        **wizard.sending_method_checkboxes,
                        'peppol': {
                            **peppol_checkbox,
                            **vals_not_valid,
                            'label': _(
                                '%(peppol_label)s%(disable_reason)s%(peppol_proxy_mode)s',
                                peppol_label=peppol_label,
                                disable_reason=addendum_disable_reason,
                                peppol_proxy_mode=addendum_mode,
                            ),
                        }
                    }

    def action_send_and_print(self, allow_fallback_pdf=False):
        # EXTENDS 'account'
        self.ensure_one()
        if self.sending_methods and 'peppol' in self.sending_methods:
            if self.move_id.partner_id.commercial_partner_id.peppol_verification_state != 'valid':
                raise UserError(_("Partner doesn't have a valid Peppol configuration."))
            if self.move_id.company_id._have_unauthorized_peppol_parent_company():
                raise AccessError(_("You are not allowed to send invoice on behalf of %s.",
                                    self.move_id.company_id.peppol_parent_company_id.sudo().name))  # sudo needed because the current user does not have access
            if registration_action := self._do_peppol_pre_send(self.move_id):
                return registration_action
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
