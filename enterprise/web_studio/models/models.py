from odoo import api, models


class Model(models.AbstractModel):
    _inherit = 'base'

    @api.model
    @api.readonly
    def get_views(self, views, options=None):
        result = super().get_views(views, options=options)
        related_models = result['models']
        self_sudo = self.sudo()
        read_group_result = self_sudo.env['studio.approval.rule']._read_group(
            [('model_name', 'in', tuple(related_models))],
            ['model_name'],
        )
        has_approval_rules = {model_name for [model_name] in read_group_result}
        for model_name in related_models:
            related_models[model_name]['has_approval_rules'] = model_name in has_approval_rules
        return result
