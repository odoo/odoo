# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_move_state = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('processing', 'Processing'),
            ('canceled', 'Canceled'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        string='PEPPOL status',
        copy=False,
        readonly=True,
    )

    def _need_ubl_cii_xml(self):
        self.ensure_one()

        res = super()._need_ubl_cii_xml()
        partner = self.partner_id
        if partner.ubl_cii_format in {False, 'facturx', 'oioubl_201'}:
            return res
        if not partner.peppol_eas or not partner.peppol_endpoint:
            return False
        if partner.account_peppol_verification_label == 'not_verified':
            partner.button_account_peppol_check_partner_endpoint()
        return res and partner.account_peppol_is_endpoint_valid

    def action_cancel_peppol_documents(self):
        # if the peppol_move_state is processing/done
        # then it means it has been already sent to peppol proxy and we can't cancel
        if any(move.peppol_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to PEPPOL"))
        self.peppol_move_state = 'canceled'
