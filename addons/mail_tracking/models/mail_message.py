from odoo import api, fields, models
from odoo.exceptions import UserError


class MailMessage(models.Model):
    _inherit = 'mail.message'

    # tracking
    tracking_value_ids = fields.One2many(
        'mail.tracking.value', 'mail_message_id',
        string='Tracking values',
        groups="base.group_system",
        help='Tracked values are stored in a separate model. This field allow to reconstruct '
             'the tracking and to generate statistics on the model.')

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)
        for record, vals in zip(self, vals_list):
            if 'message_type' in default and default.get('message_type') != 'tracking' and record.sudo().tracking_value_ids:
                raise UserError(self.env._(
                    "You cannot change message type while copying a message that contains tracking values."
                ))
            vals['tracking_value_ids'] = [(0, 0, tracking_vals) for tracking_vals in record.sudo().tracking_value_ids.copy_data()]
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        # delegate creation of tracking after the create as sudo to avoid access rights issues
        tracking_values_list = []
        for values in vals_list:
            tracking_values_list.append(values.pop('tracking_value_ids', False))
        messages = super().create(vals_list)
        messages._create_tracking_data(tracking_values_list)
        return messages

    def _create_tracking_data(self, tracking_values_ids_list):
        for message, tracking_values_cmd in zip(self, tracking_values_ids_list):
            if not tracking_values_cmd:
                continue
            track_vals_lst = []
            for cmd in tracking_values_cmd:
                if len(cmd) == 3 and cmd[0] == 0:
                    track_values = dict(cmd[2])  # copy to avoid altering original dict
                    for key in (k for k in ('field_name', 'field_label', 'field_type', 'new_value', 'old_value', 'company_name') if k in cmd[2]):
                        track_values.pop(key)
                    track_values['mail_message_id'] = message.id
                    track_vals_lst.append(track_values)
            other_cmd = [cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0]
            if track_vals_lst:
                self.env['mail.tracking.value'].sudo().create(track_vals_lst)
            if other_cmd:
                message.sudo().write({'tracking_value_ids': tracking_values_cmd})

    def _filter_empty(self):
        # override to support mail.tracking.value records in addition to tracking
        # in body
        empty_messages = super()._filter_empty()
        if empty_messages:
            empty_messages -= empty_messages.sudo().filtered('tracking_value_ids')
        return empty_messages
