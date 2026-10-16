from markupsafe import Markup

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

    def _is_empty(self):
        # override to support mail.tracking.value records in addition to tracking
        # in body
        is_empty = super()._is_empty()
        return is_empty and not (
            self.has_field_access(self._fields["tracking_value_ids"], "read")
            and self.tracking_value_ids
        )

    # ------------------------------------------------------
    # LEGACY TRACKING FALLBACK (upgrade transition)
    # ------------------------------------------------------
    # Until the post-upgrade cron finishes, retrofit the tracking values from the
    # mail.tracking.value table.

    def _store_message_fields(self, res, **kwargs):
        super()._store_message_fields(res, **kwargs)
        bodies = self._legacy_tracking_bodies_by_id()
        if not bodies:
            return
        # spoof message_type='tracking' so we get o_track layout class in UI too
        for name in ("body", "message_type"):
            if name in res.data:
                res.data.remove(name)
        res.attr("body", value=lambda m: bodies.get(m.id, m.body))
        res.attr("message_type", value=lambda m: 'tracking' if m.id in bodies else m.message_type)

    def _legacy_tracking_bodies_by_id(self):
        # message_post()/message_log() always used 'notification' for tracking msgs
        if not (candidates := self.filtered(lambda m: m.message_type == 'notification')):
            return

        # tracking values are system only: sudo + filter with _filter_has_field_access() below
        candidates_sudo = candidates.sudo()
        result = {}
        for message, message_sudo in zip(candidates, candidates_sudo):
            trackings = message_sudo.tracking_value_ids._filter_has_field_access(self.env)
            if trackings:
                result[message.id] = self._legacy_tracking_body(message.body, trackings)
        return result

    def _legacy_tracking_body(self, body, trackings):
        parts = [self._legacy_tracking_line(t) for t in trackings]
        return Markup('').join(parts) + Markup('<br>') + (body or Markup(''))

    def _legacy_tracking_line(self, tracking):
        """Return the HTML fragment for a single mail.tracking.value row."""
        info = tracking.field_info or {}
        # for a removed field, field_id is unlinked (ondelete='set null')
        # and type/label live in field_info
        ttype = (tracking.field_id and tracking.field_id.ttype) or info.get('type') or 'char'
        label = (tracking.field_id and tracking.field_id.field_description) or info.get('desc') or ''

        if ttype in ('char', 'text', 'selection', 'many2one', 'one2many', 'many2many'):
            # we already stored resolved labels (display_name for
            # m2o, joined display_names for x2m, selection label) in the
            # *_char / *_text columns
            old = tracking.old_value_char or tracking.old_value_text or 'None'
            new = tracking.new_value_char or tracking.new_value_text or 'None'
        elif ttype == 'integer':
            old = str(tracking.old_value_integer or 0)
            new = str(tracking.new_value_integer or 0)
        elif ttype in ('float', 'monetary'):
            old = f'{tracking.old_value_float or 0:.2f}'
            new = f'{tracking.new_value_float or 0:.2f}'
        elif ttype == 'boolean':
            old = 'Yes' if tracking.old_value_integer else 'No'
            new = 'Yes' if tracking.new_value_integer else 'No'
        elif ttype == 'datetime':
            old = str(tracking.old_value_datetime) if tracking.old_value_datetime else 'None'
            new = str(tracking.new_value_datetime) if tracking.new_value_datetime else 'None'
        elif ttype == 'date':
            old = str(tracking.old_value_datetime.date()) if tracking.old_value_datetime else 'None'
            new = str(tracking.new_value_datetime.date()) if tracking.new_value_datetime else 'None'
        else:
            old = tracking.old_value_char or ''
            new = tracking.new_value_char or ''
        return Markup('%s<b>%s</b><i>%s</i><br>') % (old, new, label)
