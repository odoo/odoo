# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ChatbotScript(models.Model):
    _inherit = 'chatbot.script'

    has_welcome_steps = fields.Boolean(compute='_compute_has_welcome_steps')

    @api.depends('script_step_ids')
    def _compute_has_welcome_steps(self):
        for script in self:
            script.has_welcome_steps = bool(script._get_welcome_steps())

    def action_test_script(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/chatbot/%s/test' % self.id,
            'target': 'new',
        }
