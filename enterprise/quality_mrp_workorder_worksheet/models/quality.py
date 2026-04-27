
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class QualityCheck(models.Model):
    _inherit = "quality.check"

    def action_worksheet_check(self):
        self.ensure_one()
        if not self.env.context.get('quality_wizard_id'):
            wizard = self.env['quality.check.wizard'].create({
                'check_ids': [self.id],
                'current_check_id': self.id,
            })
            action = super().with_context(quality_wizard_id=wizard.id).action_worksheet_check()
        else:
            action = super().action_worksheet_check()
        if self.workorder_id and not self.env.context.get('from_worksheet'):
            return self._next()
        return action

    def action_fill_sheet(self):
        self.ensure_one()
        return self.action_quality_worksheet()
