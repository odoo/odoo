from collections import defaultdict
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL


class MailTrackingDurationMixin(models.AbstractModel):
    _name = 'mail.tracking.duration.mixin'
    _description = "Mixin to compute the time a record has spent in each value a many2one field can take"
    _inherit = ['mail.thread']

    duration_tracking = fields.Json(
        string="Status time", compute="_compute_duration_tracking",
        help="JSON that maps ids from a many2one field to seconds spent")

    # The rotting feature enables resources to mark themselves as stale if enough time has passed
    # since their stage was last updated.
    # Consult _is_rotting_feature_enabled() documentation for configuration instructions
    rotting_days = fields.Integer('Days Rotting', help='Day count since this resource was last updated',
        compute='_compute_rotting')
    is_rotting = fields.Boolean('Rotting', compute='_compute_rotting', search='_search_is_rotting')

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

    def _is_rotting_feature_enabled(self):
        """
        To enable the rotting behavior, the following must be present:

        * Stage-like model (linked by '_track_duration_field') must have a 'rotting_threshold_days' integer field
            modeling the number of days before a record rots

        * Model inheriting from duration mixin must have a 'date_last_stage_update' field tracking the last stage change


        Also consider overriding _get_rotting_depends_fields() and _get_rotting_domain().

        Certain views have access to widgets to display rotting status:
            'rotting' for kanbans, 'rotting_statusbar_duration' for forms, 'badge_rotting' for lists.

        :return: bool: whether the rotting feature has been configured for this model
        """
        return 'rotting_threshold_days' in self[self._track_duration_field] and 'date_last_stage_update' in self and (
            not self  # api.model call
            or any(stage.rotting_threshold_days for stage in self[self._track_duration_field])
        )

    def _get_rotting_depends_fields(self):
        """
        fields added to this method through override should likely also be returned by _get_rotting_domain() override

        :return: the array of fields that can affect the ability of a resource to rot
        """
        if hasattr(self, '_track_duration_field') and 'rotting_threshold_days' in self[self._track_duration_field]:
            return ['date_last_stage_update', f'{self._track_duration_field}.rotting_threshold_days']
        return []

    def _get_rotting_domain(self):
        """
        fields added to this method through override should likely also be returned by _get_rotting_depends_fields() override

        :return: domain: conditions that must be met so that the field can be considered rotting
        """
        return Domain(f'{self._track_duration_field}.rotting_threshold_days', '!=', 0)

    @api.depends(lambda self: self._get_rotting_depends_fields())
    def _compute_rotting(self):
        """
        A resource is rotting if its stage has not been updated in a number of days depending on its
        stage's rotting_threshold_days value, assuming it matches _get_rotting_domain() conditions.

        If the rotting_threshold_days field is not defined on the tracked module,
        or if the value of rotting_threshold_days is 0,
        then the resource will never rot.
        """
        if not self._is_rotting_feature_enabled():
            self.is_rotting = False
            self.rotting_days = 0
            return
        now = self.env.cr.now()
        rot_enabled = self.filtered_domain(self._get_rotting_domain())
        others = self - rot_enabled
        for stage, records in rot_enabled.grouped(self._track_duration_field).items():
            rotting = records.filtered(lambda record:
                (record.date_last_stage_update or record.create_date or fields.Datetime.now())
                + timedelta(days=stage.rotting_threshold_days) < now
            )
            for record in rotting:
                record.is_rotting = True
                record.rotting_days = (now - (record.date_last_stage_update or record.create_date)).days
            others += records - rotting
        others.is_rotting = False
        others.rotting_days = 0

    def _search_is_rotting(self, operator, value):
        if operator not in ['in', 'not in']:
            raise ValueError(self.env._('For performance reasons, use "=" operators on rotting fields.'))
        if not self._is_rotting_feature_enabled():
            raise UserError(self.env._('Model configuration does not support the rotting feature'))

        stage_fname = self._track_duration_field
        Stage = self.env[self._fields[stage_fname].comodel_name]
        now = self.env.cr.now()
        max_rotting_months = int(self.env['ir.config_parameter'].sudo().get_param('crm.lead.rot.max.months', default=12))
        oldest_considered = now - relativedelta(months=max_rotting_months)
        stages = Stage.sudo().with_context(active_test=False).search_fetch(
            [('rotting_threshold_days', '!=', 0)], ['rotting_threshold_days'],
        )
        rotting = Domain.OR(
            Domain(stage_fname, 'in', stages_with_threshold.ids)
            & Domain('date_last_stage_update', '>', oldest_considered)
            & Domain('date_last_stage_update', '<=', now - timedelta(days=threshold))
            for threshold, stages_with_threshold in stages.grouped('rotting_threshold_days').items()
        ) & Domain(self._get_rotting_domain())

        is_rotting_searched = (operator == 'in') == (True in value)
        return rotting if is_rotting_searched else ~rotting
