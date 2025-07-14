from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class MailTrackingDurationMixin(models.AbstractModel):
    _name = 'mail.tracking.duration.mixin'
    _description = "Mixin to compute the time a record has spent in each value a many2one field can take"
    _inherit = ['mail.thread']

    duration_tracking = fields.Json(
        string="Status time", compute="_compute_duration_tracking",
        help="JSON that maps ids from a many2one field to seconds spent")

    def _compute_duration_tracking(self):
        """
        Computes duration_tracking, a Json field stored as { <many2one_id (str)>: <duration_spent_in_seconds (int)> }

            e.g. {"1": 1230, "2": 2220, "5": 14}

        `_track_duration_field` must be present in the model that uses the mixin to specify on what
        field to compute time spent. Besides, tracking must be activated for that field.

            e.g.
            class MyModel(models.Model):
                _name = 'my.model'
                _track_duration_field = "tracked_field"

                tracked_field = fields.Many2one('tracked.model', tracking=True)
        """

        field = self.env['ir.model.fields'].sudo().search_fetch([
            ('model', '=', self._name),
            ('name', '=', self._track_duration_field),
        ], ['id'], limit=1)

        if (
            self._track_duration_field not in self._track_get_fields()
            or self._fields[self._track_duration_field].type != 'many2one'
        ):
            self.duration_tracking = False
            raise ValueError(_(
                'Field “%(field)s” on model “%(model)s” must be of type Many2one and have tracking=True for the computation of duration.',
                field=self._track_duration_field, model=self._name
            ))

        if self.ids:
            self.env['mail.tracking.value'].flush_model()
            self.env['mail.message'].flush_model()
            trackings = self.env.execute_query_dict(SQL("""
                   SELECT m.res_id,
                          v.create_date,
                          v.old_value_integer
                     FROM mail_tracking_value v
                LEFT JOIN mail_message m
                       ON m.id = v.mail_message_id
                      AND v.field_id = %(field_id)s
                    WHERE m.model = %(model_name)s
                      AND m.res_id IN %(record_ids)s
                 ORDER BY v.id
                """,
                field_id=field.id, model_name=self._name, record_ids=tuple(self.ids),
            ))
        else:
            trackings = []

        for record in self:
            record_trackings = [tracking for tracking in trackings if tracking['res_id'] == record._origin.id]
            record.duration_tracking = record._get_duration_from_tracking(record_trackings)

    def _get_duration_from_tracking(self, trackings):
        """
        Calculates the duration spent in each value based on the provided list of trackings.
        It adds a "fake" tracking at the end of the trackings list to account for the time spent in the current value.

        Args:
            trackings (list): A list of dictionaries representing the trackings with:
                - 'create_date': The date and time of the tracking.
                - 'old_value_integer': The ID of the previous value.

        Returns:
            dict: A dictionary where the keys are the IDs of the values, and the values are the durations in seconds
        """
        self.ensure_one()
        json = defaultdict(lambda: 0)
        previous_date = self.create_date or self.env.cr.now()

        # If there is a tracking value to be created, but still in the
        # precommit values, create a fake one to take it into account.
        # Otherwise, the duration_tracking value will add time spent on
        # previous tracked field value to the time spent in the new value
        # (after writing the stage on the record)
        if f'mail.tracking.{self._name}' in self.env.cr.precommit.data:
            if data := self.env.cr.precommit.data.get(f'mail.tracking.{self._name}', {}).get(self._origin.id):
                new_id = data.get(self._track_duration_field, self.env[self._name]).id
                if new_id and new_id != self[self._track_duration_field].id:
                    trackings.append({
                        'create_date': self.env.cr.now(),
                        'old_value_integer': data[self._track_duration_field].id,
                    })

        # add "fake" tracking for time spent in the current value
        trackings.append({
            'create_date': self.env.cr.now(),
            'old_value_integer': self[self._track_duration_field].id,
        })

        for tracking in trackings:
            json[tracking['old_value_integer']] += int((tracking['create_date'] - previous_date).total_seconds())
            previous_date = tracking['create_date']

        return json

    """
    Rotting logic

    The rotting feature enables resources to mark themselves as stale if enough time has passed since they were last updated
    by an user.
    To enable this behavior, the following must be done:
    - The model pointed to by _track_duration_field must have a "rotting_threshold_days" integer field, representing the
    number of days before the resource is considered stale:
        on the model pointed to by _track_duraton_field:
            rotting_threshold_days = fields.Integer('Days to rot', default=0)

    - The following methods need to be overriden:
      - _get_rotting_depends_fields() must be overriden to include the rotting_threshold_days field, as well as
        any field that should affect the ability of a resource to rot (for example: a field that would mark a task as done):
            def _get_rotting_depends_fields(self):
                return super()._get_rotting_depends_fields() + ['won_status', 'type']

      - _get_rotting_domain() must be overriden to include conditions that must be met so that the field can be considered rotting:
            def _get_rotting_domain(self):
                return super()._get_rotting_domain() + [
                    ('won_status', '=', 'pending'),
                    ('type', '=', 'opportunity')
                ]

        Note that the fields present in _get_rotting_domain() are the same as the ones present in _get_rotting_depends_fields()

    - The is_rotting, rotting_days fields need to be added to the relevant views
        (as well as the "rotting_threshold_days" field on the tracked model).
        You may want to use the rotting_form, rotting_kanban and rotting_badge_list field widgets to display
        the fields visually on form and kanban view
        (please note- these widgets need both rotting_days and is_rotting fields on the view to function).

    If the rotting_threshold_days field is not defined on the tracked module,
    or if the value of rotting_threshold_days is 0,
    then the resource will never rot.
    """

    rotting_days = fields.Integer('Days Rotting', help='Day count since this resource was last updated',
        compute='_compute_rotting', store=False)
    is_rotting = fields.Boolean('Rotting', compute='_compute_rotting', search='_search_is_rotting')
    rotting_date = fields.Date('Rotting Since', help='Date at which the resource starts rotting',
        compute="_compute_rotting_date", store=True, readonly=False)

    # To override in inheriting models
    def _get_rotting_depends_fields(self):
        return []

    # To override in inheriting models
    def _get_rotting_domain(self):
        return [
            ('rotting_date', '<=', fields.Datetime.today()),
            ('rotting_date', '!=', False),
            (f'{self._track_duration_field}.rotting_threshold_days', '!=', 0),
        ]

    def _is_rotting_enabled(self):
        return hasattr(self, '_track_duration_field') and 'rotting_threshold_days' in self[self._track_duration_field] and (
                not self  # api.model call
                or any(stage.rotting_threshold_days for stage in self[self._track_duration_field])
            )

    @api.depends(lambda self: ['write_date'] + self._get_rotting_depends_fields())
    def _compute_rotting_date(self):
        """
        We purposefully do not update the rotting date if rotting_threshold_days is changed.
        This is done to avoid having to update a large amount of records at once.
        Records will be naturally updated once they get any kind of activity.
        """
        if not self._is_rotting_enabled():
            self.rotting_date = False
            return

        # As we want the rotting date to update even for records that aren't rotting yet,
        # we remove tuples referencing 'rotting_date' from the domain
        domain = [tup for tup in self._get_rotting_domain() if tup[0] != 'rotting_date']
        rotting_self = self.filtered_domain(domain)

        (self - rotting_self).rotting_date = False
        stages = rotting_self[self._track_duration_field]
        stages = rotting_self.mapped(self._track_duration_field)
        for stage in stages:
            stage_resources = rotting_self.filtered(lambda r: r[self._track_duration_field] == stage)
            for resource in stage_resources:
                resource.rotting_date = (resource.write_date or fields.Datetime.now()) + timedelta(days=stage.rotting_threshold_days)

    def _message_post_after_hook(self, message, msg_values):
        # todo todelete review note:
        # As per specs, resources' rotting date should be refreshed once an activity gets marked as done.
        # Originally this was ensured by checking for the 'notification' message_type, however this might lead
        # to inaccurate results when other flows get involved, as 'notification' is the default message type for
        # message_post() and message_post_with_source()
        # As the XMLID subtype for done activities ('mail.mt_activities') isn't passed on to msg_values, I figured it was
        # appropriate to check for presence of 'mail_activity_type_id' in msg_values. Does that make sense?

        if msg_values['message_type'] in ['email_outgoing', 'comment'] or msg_values.get('mail_activity_type_id', False):
            # If rotting_threshold_days field has not been set, the rotting feature is not enabled for this model.

            # sudo to read rotting_threshold_days even if the user doesn't normally have access to the tracked model's fields
            self_sudo = self.sudo()
            if self_sudo._is_rotting_enabled():
                self_sudo = self_sudo.filtered_domain(self_sudo._get_rotting_domain())
                rotting_threshold_days = self_sudo[self._track_duration_field].rotting_threshold_days if self_sudo else 0
                if rotting_threshold_days > 0:
                    self.rotting_date = fields.Datetime.now() + timedelta(days=rotting_threshold_days)
        return super()._message_post_after_hook(message, msg_values)

    @api.depends(lambda self: ['rotting_date'] + self._get_rotting_depends_fields())
    def _compute_rotting(self):
        rotting_records = self.filtered_domain(self._get_rotting_domain() if self._is_rotting_enabled() else fields.Domain.FALSE)
        rotting_records.is_rotting = True
        for record in rotting_records:
            record.rotting_days = (fields.Datetime.now().date() - record.rotting_date).days + record[self._track_duration_field].rotting_threshold_days
        (self - rotting_records).is_rotting = False
        (self - rotting_records).rotting_days = 0

    def _search_is_rotting(self, operator, value):
        """
        :param operator
        :param value
        :return domain

        Override this search method to complete the search domain for is_rotting field
        """
        if operator not in ['in', 'not in']:
            raise UserError(_('Operation not supported'))

        rotting_domain = self._get_rotting_domain() if self._is_rotting_enabled() else [fields.Domain.FALSE]
        if operator == 'in':
            return rotting_domain
        domain = fields.Domain.AND([[tuple] for tuple in rotting_domain])
        return ['!', domain]
