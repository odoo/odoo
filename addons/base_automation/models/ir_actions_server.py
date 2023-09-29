# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _


class ServerAction(models.Model):
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
