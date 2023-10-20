from collections import defaultdict

from odoo import _, fields, models


class MailTrackingDurationMixin(models.AbstractModel):
    _name = "mail.tracking.duration.mixin"
    _description = "Mixin to compute the time a record has spent in each value a many2one field can take"

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
                'Field "(field)r on model %(model)r must be of type Many2one and have tracking=True for the computation of duration.',
                field=self._track_duration_field, model=self._name
            ))

        self.env['mail.tracking.value'].flush_model()
        self.env['mail.message'].flush_model()
        query = """
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
        """
        self.env.cr.execute(query, {"field_id": field.id, "model_name": self._name, "record_ids": tuple(self.ids)})
        trackings = self.env.cr.dictfetchall()

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
        previous_date = self.create_date

        # add "fake" tracking for time spent in the current value
        trackings.append({
            'create_date': self.env.cr.now(),
            'old_value_integer': self[self._track_duration_field].id,
        })

        for tracking in trackings:
            json[tracking['old_value_integer']] += int((tracking['create_date'] - previous_date).total_seconds())
            previous_date = tracking['create_date']

        return json
