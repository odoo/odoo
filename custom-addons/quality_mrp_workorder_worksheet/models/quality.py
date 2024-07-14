
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class QualityCheck(models.Model):
    _inherit = "quality.check"

    def action_worksheet_check(self):
        self.ensure_one()
        action = super().action_worksheet_check()
        if self.workorder_id and not self.env.context.get('from_worksheet'):
            return self._next()
        return action

    def action_fill_sheet(self):
        self.ensure_one()
        # we need to access the worksheet through the wizard to do the checks
        return self.action_open_quality_check_wizard()
