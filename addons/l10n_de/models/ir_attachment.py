# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=True)
    def _except_audit_trail(self):
        for attachment in self:
            if attachment.res_model == 'account.move' and attachment.res_id:
                move = self.env['account.move'].browse(attachment.res_id)
                if move.posted_before and move.country_code == 'DE':
                    raise UserError(_("You cannot remove parts of the audit trail. Archive the record instead."))
