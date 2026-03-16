from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    # tracking
    tracking_value_ids = fields.One2many(
        'mail.tracking.value', 'mail_message_id',
        string='Tracking values',
        groups="base.group_system",
        help='Tracked values are stored in a separate model. This field allow to reconstruct '
             'the tracking and to generate statistics on the model.')

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
                    for key in (k for k in ('field_name', 'field_label', 'field_type', 'new_value', 'old_value') if k in cmd[2]):
                        track_values.pop(key)
                    track_values['mail_message_id'] = message.id
                    track_vals_lst.append(track_values)
            other_cmd = [cmd for cmd in tracking_values_cmd if len(cmd) != 3 or cmd[0] != 0]
            if track_vals_lst:
                self.env['mail.tracking.value'].sudo().create(track_vals_lst)
            if other_cmd:
                message.sudo().write({'tracking_value_ids': tracking_values_cmd})
