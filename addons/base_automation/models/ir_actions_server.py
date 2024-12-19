# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.json import scriptsafe as json_scriptsafe

from odoo import api, exceptions, fields, models, _

from .base_automation import get_webhook_request_payload


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    usage = fields.Selection(selection_add=[
        ('base_automation', 'Automation Rule')
    ], ondelete={'base_automation': 'cascade'})
    base_automation_id = fields.Many2one('base.automation', string='Automation Rule', ondelete='cascade')

    @api.constrains('model_id', 'base_automation_id')
    def _check_model_coherency_with_automation(self):
        for action in self.filtered('base_automation_id'):
            if action.model_id != action.base_automation_id.model_id:
                raise exceptions.ValidationError(
                    _("Model of action %(action_name)s should match the one from automated rule %(rule_name)s.",
                      action_name=action.name,
                      rule_name=action.base_automation_id.name
                     )
                )

    @api.depends('usage')
    def _compute_available_model_ids(self):
        """ Stricter model limit: based on automation rule """
        super()._compute_available_model_ids()
        rule_based = self.filtered(lambda action: action.usage == 'base_automation')
        for action in rule_based:
            rule_model = action.base_automation_id.model_id
            action.available_model_ids = rule_model.ids if rule_model in action.available_model_ids else []

    def _can_update_name(self):
        self.ensure_one()
        return not bool(self.base_automation_id) and super()._can_update_name()

    def _get_eval_context(self, action=None):
        eval_context = super()._get_eval_context(action)
        if action and action.state == "code":
            eval_context['json'] = json_scriptsafe
            payload = get_webhook_request_payload()
            if payload:
                eval_context["payload"] = payload
        return eval_context
