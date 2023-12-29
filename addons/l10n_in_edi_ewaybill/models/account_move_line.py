# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def l10n_in_reset_draft_action(self):
        ''' posted -> draft '''
        self.move_id.button_draft()
