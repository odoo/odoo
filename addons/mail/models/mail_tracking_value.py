# -*- coding: utf-8 -*-
from odoo import fields, models


class MailTrackingValue(models.Model):
    _name = 'mail.tracking.value'
    _description = 'Mail Tracking Value'
    _rec_name = 'field_id'
    _order = 'id DESC'

    field_id = fields.Many2one(
        'ir.model.fields', required=False, readonly=True,
        index=True, ondelete='set null')
    field_info = fields.Json('Removed field information')

    old_value_integer = fields.Integer('Old Value Integer', readonly=True)
    old_value_float = fields.Float('Old Value Float', readonly=True)
    old_value_char = fields.Char('Old Value Char', readonly=True)
    old_value_text = fields.Text('Old Value Text', readonly=True)
    old_value_datetime = fields.Datetime('Old Value DateTime', readonly=True)

    new_value_integer = fields.Integer('New Value Integer', readonly=True)
    new_value_float = fields.Float('New Value Float', readonly=True)
    new_value_char = fields.Char('New Value Char', readonly=True)
    new_value_text = fields.Text('New Value Text', readonly=True)
    new_value_datetime = fields.Datetime('New Value Datetime', readonly=True)

    mail_message_id = fields.Many2one('mail.message', 'Message ID', required=True, index=True, ondelete='cascade')

    def _filter_has_field_access(self, env):
        """ Return the subset of self for which the user in env has access. As
        this model is admin-only, it is generally accessed as sudo and we need
        to distinguish context environment from tracking values environment.

        If tracking is linked to a field, user should have access to the field.
        Otherwise only members of "base.group_system" can access it. """

        def has_field_access(tracking):
            if not tracking.field_id:
                return env.is_system()
            model = env[tracking.field_id.model]
            model_field = model._fields.get(tracking.field_id.name)
            return model.has_field_access(model_field, 'read') if model_field else False

        return self.filtered(has_field_access)

    def _filter_free_field_access(self):
        """ Return the subset of self which is available for all users: trackings
        linked to an existing field without access group. It is used notably
        when sending tracking summary through notifications. """

        def has_free_access(tracking):
            if not tracking.field_id:
                return False
            model_field = self.env[tracking.field_id.model]._fields.get(tracking.field_id.name)
            return model_field and not model_field.groups

        return self.filtered(has_free_access)
