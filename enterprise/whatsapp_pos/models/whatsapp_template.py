# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from odoo import api, models


class WhatsAppTemplate(models.Model):
    _inherit = 'whatsapp.template'

    @api.model
    def _find_default_for_model(self, model_name):
        if model_name == 'pos.order':
            return self.search([
                ('model', '=', model_name),
                ('status', '=', 'approved'),
                ('template_type', '=', 'marketing'),
                '|',
                    ('allowed_user_ids', '=', False),
                    ('allowed_user_ids', 'in', self.env.user.ids)
            ], limit=1)
        return super()._find_default_for_model(model_name)

    def button_create_action(self):
        actions = super().button_create_action()
        for action in actions:
            if action.binding_model_id.model == 'pos.order':
                action.context = repr(dict(literal_eval(action.context)) | {'template_types': ['marketing']})
        return actions
