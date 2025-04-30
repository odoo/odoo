# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.json import scriptsafe as json_scriptsafe

from odoo import api, fields, models, _
from odoo.fields import Domain

from .base_automation import get_webhook_request_payload


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    usage = fields.Selection(selection_add=[
        ('base_automation', 'Automation Rule')
    ], ondelete={'base_automation': 'cascade'})
    base_automation_id = fields.Many2one('base.automation', string='Automation Rule', index='btree_not_null', ondelete='cascade')

    @api.model
    def _warning_depends(self):
        return super()._warning_depends() + [
            'model_id',
            'base_automation_id',
        ]

    def _get_warning_messages(self):
        self.ensure_one()
        warnings = super()._get_warning_messages()

        if self.base_automation_id and self.model_id != self.base_automation_id.model_id:
            warnings.append(
                _("Model of action %(action_name)s should match the one from automated rule %(rule_name)s.",
                    action_name=self.name,
                    rule_name=self.base_automation_id.name
                    )
            )

        return warnings

    def _get_children_domain(self):
        # As automation rules' actions does not have a parent,
        # we make sure multi actions can not link to automation rules' actions.
        return super()._get_children_domain() & Domain("base_automation_id", "=", False)

    @api.depends('usage')
    def _compute_available_model_ids(self):
        """ Stricter model limit: based on automation rule """
        super()._compute_available_model_ids()
        rule_based = self.filtered(lambda action: action.usage == 'base_automation')
        for action in rule_based:
            rule_model = action.base_automation_id.model_id
            action.available_model_ids = rule_model.ids if rule_model in action.available_model_ids else []

    def _get_eval_context(self, action=None):
        eval_context = super()._get_eval_context(action)
        if action and action.state == "code":
            eval_context['json'] = json_scriptsafe
            payload = get_webhook_request_payload()
            if payload:
                eval_context["payload"] = payload
        return eval_context

    def action_open_automation(self):
        return {
            "type": "ir.actions.act_window",
            "target": "current",
            "views": [[False, "form"]],
            "res_model": self.base_automation_id._name,
            "res_id": self.base_automation_id.id,
        }


# Also extend IrCron because of missing methods due to delegation inheritance
class IrCron(models.Model):
    _inherit = "ir.cron"

    def action_open_automation(self):
        return self.ir_actions_server_id.action_open_automation()
