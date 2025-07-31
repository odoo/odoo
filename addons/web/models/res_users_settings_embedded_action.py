from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsersSettingsEmbeddedAction(models.Model):
    _name = 'res.users.settings.embedded.action'
    _description = 'User Settings for Embedded Actions'

    user_setting_id = fields.Many2one('res.users.settings', required=True, ondelete='cascade', index='btree_not_null', export_string_translation=False)
    action_id = fields.Many2one('ir.actions.act_window', required=True, ondelete='cascade', export_string_translation=False)
    res_model = fields.Char(required=True, export_string_translation=False)
    res_id = fields.Integer(export_string_translation=False)
    embedded_actions_order = fields.Char('List order of embedded action ids', export_string_translation=False)
    embedded_actions_visibility = fields.Char('List visibility of embedded actions ids', export_string_translation=False)
    embedded_visibility = fields.Boolean('Is top bar visible', export_string_translation=False)

    _res_user_settings_embedded_action_unique = models.Constraint(
        'UNIQUE (user_setting_id, action_id, res_id)',
        'The user should have one unique embedded action setting per user setting, action and record id.',
    )

    @api.constrains('embedded_actions_order')
    def _check_embedded_actions_order(self):
        self._check_embedded_actions_field_format('embedded_actions_order')

    @api.constrains('embedded_actions_visibility')
    def _check_embedded_actions_visibility(self):
        self._check_embedded_actions_field_format('embedded_actions_visibility')

    def _check_embedded_actions_field_format(self, field_name):
        for setting in self:
            value = setting[field_name]
            if not value:
                return
            action_ids = value.split(',')
            if len(action_ids) != len(set(action_ids)):
                raise ValidationError(
                    self.env._(
                        'The ids in %(field_name)s must not be duplicated: “%(action_ids)s”',
                        field_name=field_name,
                        action_ids=action_ids,
                    )
                )
            for action_id in action_ids:
                if not (action_id.isdigit() or action_id == 'false'):
                    raise ValidationError(
                        self.env._(
                            'The ids in %(field_name)s must only be integers or "false": “%(action_ids)s”',
                            field_name=field_name,
                            action_ids=action_ids,
                        )
                    )

    def _embedded_action_settings_format(self):
        return {
            f'{setting.action_id.id}+{setting.res_id or ""}': {
                'embedded_actions_order': [
                    False if action_id == 'false' else int(action_id) for action_id in setting.embedded_actions_order.split(',')
                ] if setting.embedded_actions_order else [],
                'embedded_actions_visibility': [
                    False if action_id == 'false' else int(action_id) for action_id in setting.embedded_actions_visibility.split(',')
                ] if setting.embedded_actions_visibility else [],
                'embedded_visibility': setting.embedded_visibility,
            }
            for setting in self
        }
