# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    sale_note = fields.Text(string='Default Terms and Conditions', translate=True)
    portal_confirmation_sign = fields.Boolean(string='Digital Signature')
    portal_confirmation_pay = fields.Boolean(string='Electronic Payment')

    @api.depends('portal_confirmation_sign')
    def _get_sale_onboarding_signature_radio(self):
        """ Convert portal_confirmation_sign from boolean to radio. """
        for record in self:
            record.portal_confirmation_sign_radio = 'yes' if record.portal_confirmation_sign else 'no'

    @api.depends('portal_confirmation_sign')
    def _set_sale_onboarding_signature_radio(self):
        """ Convert portal_confirmation_sign from radio to boolean. """
        for record in self:
            record.portal_confirmation_sign = record.portal_confirmation_sign_radio == 'yes'

    # the target field, portal_confirmation_sign, is a boolean but we would like to render it as a radio button
    portal_confirmation_sign_radio = fields.Selection([('yes', "Yes"), ('no', "No")], "Digital Signature (radio)",
        compute=_get_sale_onboarding_signature_radio, inverse=_set_sale_onboarding_signature_radio)

    # sale quotation onboarding
    sale_quotation_onboarding_closed = fields.Boolean(
        string="Onboarding sale quotation closed",
        help="Refers to the sale quotation onboarding panel closed state.")
    sale_quotation_onboarding_folded = fields.Boolean(
        string="Onboarding sale quotation folded",
        help="Refers to the sale quotation onboarding panel folded state.")
    sale_onboarding_quotation_layout_done = fields.Boolean("Onboarding quotation layout step done",
        compute="_compute_sale_onboarding_quotation_layout_done")
    sale_onboarding_payment_acquirer_done = fields.Boolean("Sale onboarding payment acquirer step done",
        default=False)
    sale_onboarding_signature_done = fields.Boolean("Sale onboarding signature step done",
        default=False)

    @api.model
    def action_toggle_fold_sale_quotation_onboarding(self):
        """ Toggle the onboarding panel `folded` state. """
        self.env.user.company_id.sale_quotation_onboarding_folded =\
            not self.env.user.company_id.sale_quotation_onboarding_folded

    @api.model
    def action_close_sale_quotation_onboarding(self):
        """ Mark the onboarding panel as closed. """
        self.env.user.company_id.sale_quotation_onboarding_closed = True

    @api.model
    def action_open_sale_onboarding_signature(self):
        """ Called by onboarding panel above the quotation list."""
        action = self.env.ref('sale.action_open_sale_onboarding_signature').read()[0]
        action['res_id'] = self.env.user.company_id.id
        return action

    @api.model
    def action_open_sale_onboarding_payment_acquirer(self):
        """ Called by onboarding panel above the quotation list."""
        action = self.env.ref('sale.action_open_sale_onboarding_payment_acquirer_wizard').read()[0]
        return action

    @api.multi
    def action_save_onboarding_signature(self):
        self.sale_onboarding_signature_done = True
