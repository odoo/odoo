# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrResumeLineType(models.Model):
    _inherit = ['hr.resume.line.type']

    @api.ondelete(at_uninstall=False)
    def _unlink_except_event_type(self):
        if self.env['hr.resume.line'].get_event_type_id() in self.ids:
            raise UserError(_("Event resume line type cannot be deleted"))
