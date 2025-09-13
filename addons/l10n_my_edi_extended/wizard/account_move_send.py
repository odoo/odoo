# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import str2bool


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    @api.depends('move_ids')
    def _compute_l10n_my_edi_enable(self):
        """ Override to disable the usage of MyInvois in the Send & Print wizard.
        It is not fully compatible with the QR flow and thus, we intend to send the file to MyInvois separately.
        """
        super()._compute_l10n_my_edi_enable()
        for wizard in self:
            # In master, the send & print sending flow will be fully removed and this won't be needed anymore.
            # For now, this is kept so that runbot won't fail the base module tests, which we still want to run atm.
            disabled = str2bool(self.env['ir.config_parameter'].sudo().get_param('l10n_my_edi.disable.send_and_print.first', 'True'))
            wizard.l10n_my_edi_enable = not disabled and wizard.l10n_my_edi_enable
