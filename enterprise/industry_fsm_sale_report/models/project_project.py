# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.onchange('allow_billable')
    def _onchange_allow_billable(self):
        if not self.is_fsm and not self.allow_billable:
            self.allow_worksheets = False

    @api.onchange('allow_worksheets')
    def _onchange_allow_worksheets(self):
        if not self.is_fsm and self.allow_worksheets:
            self.allow_billable = True
