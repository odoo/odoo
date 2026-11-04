# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import str2bool


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_my_edi_applicable(self, move):
        """ Override to disable the usage of MyInvois in the Send & Print wizard.
        It is not fully compatible with the QR flow and thus, we intend to send the file to MyInvois separately.
        """
        is_applicable = super()._is_my_edi_applicable(move)
        disabled = str2bool(self.env['ir.config_parameter'].sudo().get_param('l10n_my_edi.disable.send_and_print.first', 'True'))
        return is_applicable and not disabled
