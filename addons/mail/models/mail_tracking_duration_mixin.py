from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class MailThreadTrackingDurationMixin(models.AbstractModel):
    _name = 'mail.thread.tracking.duration.mixin'
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
    - The model pointed to by _track_duration_field must have a "Days to rot" integer field, representing the number of days before
    the resource is considered stale. That field must be identified on the inheriting model by setting _stage_day_rot_field:
        on the inheriting model:
            self._stage_day_rot_field = "day_rot"
        on the model pointed to by _track_duraton_field:
            day_rot = fields.Integer('Days to rot', default=0)

    - Several methods must be extended/overriden:
      - _resource_is_not_rotting_hook(task) must be overriden to add additional conditions for which a stage IS NOT rotting
        (e.g. a task that has been closed):
            def _resource_is_not_rotting_hook(self, task):
                if task.is_closed:
                    return True
                return super()._resource_is_not_rotting_hook(task)
      - _compute_is_rotting() must be overriden to update its @depends to trigger if the "days to rot" field is updated,
        or if the variables on which _resource_is_not_rotting_hook() override depends are modified:
            @api.depends('is_closed', 'stage_id.day_rot')
            def _compute_rotting(self):
                super()._compute_rotting()
      - _search_is_rotting() should be overriden to update the returned domain with additional conditions for which a stage COULD BE rotting
        (AND condition, all need to be true):
            def _search_is_rotting(self, operator, value):
                sup = super()._search_is_rotting(operator, value)
                return Domain.AND([sup, [('is_closed', '=', True)]])

    - The is_rotting, day_rotting, last_activity fields need to be added to the relevant views
        (as well as the "days to rot" field on the tracked model).
        You may want to use the rotting_form and rotting_kanban field widgets to display the fields visually on form and kanban view
        (please note- these widgets need both day_rotting and is_rotting fields on the view to function).


    Note that if _stage_day_rot_field is not set, or if the value stored by the field pointed by _stage_day_rot_field is 0,
    then the resource will never rot.
    """

    is_rotting = fields.Boolean('Rotting', compute='_compute_rotting', search='_search_is_rotting')
    day_rotting = fields.Integer('Days Rotting', help='Day count since this resource was last updated',
        compute='_compute_rotting')
    last_activity = fields.Date('Date of last activity', compute="_compute_last_activity", store=True, readonly=False)

    @api.depends('write_date')
    def _compute_last_activity(self):
        for resource in self:
            resource.last_activity = resource.write_date or self.env.cr.now()

    def _get_day_count_to_rotting(self) -> int:
        """
        :return: day count before the resource is considered to be rotting
        """
        self.ensure_one()
        rotting_stage = self[self._track_duration_field]
        if not rotting_stage or not hasattr(self, '_stage_day_rot_field'):
            # If _stage_day_rot_field has not been set, the rotting feature is not enabled for this model
            return 0
        if not self._stage_day_rot_field in rotting_stage:
            raise UserError(_('Models using the rotting feature need to declare a "day_rot" field on their stage model. Please refer to the help present in the mail/models/mail_tracking_duration_mixin.py file for implementation details'))
        day_rot = rotting_stage[self._stage_day_rot_field]
        return day_rot

    def _message_post_after_hook(self, message, msg_values):
        if msg_values['message_type'] in ['email_outgoing', 'comment', 'notification']:
            self.write({'last_activity': self.env.cr.now()})
        return super()._message_post_after_hook(message, msg_values)

    @api.depends('last_activity')
    def _compute_rotting(self):
        for resource in self:
            if self._resource_is_not_rotting_hook(resource):
                resource.is_rotting = False
                resource.day_rotting = 0
            else:
                resource.is_rotting = True
                resource.day_rotting = (fields.Date.today() - resource.last_activity).days

    def _resource_is_not_rotting_hook(self, resource) -> bool:
        """
        :param resource
        :return: True if the resource is fresh

        Override this hook to add new conditions for which the resource is not rotting
        (e.g. the resource not being of a type that can rot, or being in a "finish" condition.)
        Don't forget to also override _compute_rotting with the new @api.depends, based on the fields you use
        """
        return resource._get_day_count_to_rotting() == 0 or fields.Date.today() < resource.last_activity + relativedelta(days=resource._get_day_count_to_rotting())

    def _search_is_rotting(self, operator, value):
        """
        :param operator
        :param value
        :return domain

        Override this search method to complete the search domain for is_rotting field
        """
        if operator not in ['in', 'not in']:
            raise UserError(_('Operation not supported'))

        query = """
            WITH innerTable AS (
                SELECT %(table)s.id AS id, (%(table)s.last_activity + %(stage_table)s.%(day_rot_field)s) AS date_rot
                FROM %(table)s
                    INNER JOIN %(stage_table)s
                    ON %(stage_table)s.id = %(table)s.%(stage_field)s
                WHERE
                    %(stage_table)s.%(day_rot_field)s != 0
            )
            SELECT id
            FROM innerTable
            WHERE %(today)s >= date_rot
        """
        self.env.cr.execute(SQL(query,
            table=SQL.identifier(self._table),
            stage_table=SQL.identifier(self[self._track_duration_field]._table),
            stage_field=SQL.identifier(self._track_duration_field),
            day_rot_field=SQL.identifier(self._stage_day_rot_field),
            today=fields.Date.context_today(self),
        ))
        rows = self.env.cr.dictfetchall()
        return [('id', operator, [r['id'] for r in rows])]
