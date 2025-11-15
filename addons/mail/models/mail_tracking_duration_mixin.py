from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL


class MailTrackingDurationMixin(models.AbstractModel):
    _name = 'mail.tracking.duration.mixin'
    _description = "Mixin to compute the time a record has spent in each value a many2one field can take"
    _inherit = ['mail.thread']

    duration_tracking = fields.Json(
        string="Status time", compute="_compute_duration_tracking",
        store=True,
        help="JSON that maps ids from a many2one field to seconds spent")

    # The rotting feature enables resources to mark themselves as stale if enough time has passed
    # since their stage was last updated.
    # Consult _is_rotting_feature_enabled() documentation for configuration instructions
    rotting_days = fields.Integer('Days Rotting', help='Day count since this resource was last updated',
        compute='_compute_rotting')
    is_rotting = fields.Boolean('Rotting', compute='_compute_rotting', search='_search_is_rotting')

    @api.depends(lambda self: [self._track_duration_field])
    def _compute_duration_tracking(self):
        """
        Tracks how long a record stays in different stages.

        This method calculates elapsed time since the last stage change and stores the
        information in the `duration_tracking` dictionary.

        The dictionary keys are:
        *   d (datetime):
                The exact UTC datetime the record added the current state.
        *   s (stage id):
                The unique ID of the *current* stage the record is in.
        <stage_id> (int):
                A running total of accumulated time (in seconds) spent in previous states, mapping
            stage IDs to seconds.

        Example:
            {"d":"2025-11-21 15:34:28","s":3, "1":172814,"2":86401 }
        """
        now = self.env.cr.now()
        for record in self:
            tracking = record.duration_tracking or {}
            if record[record._track_duration_field]:
                if tracking.get('s') and tracking.get('d'):
                    prev_dt = fields.Datetime.from_string(tracking['d'])
                    key = str(tracking['s'])
                    tracking[key] = tracking.get(key, 0) + int((now - prev_dt).total_seconds())
                tracking['s'] = record[record._track_duration_field].id
                tracking['d'] = fields.Datetime.to_string(now)
                record.duration_tracking = tracking

    def _is_rotting_feature_enabled(self):
        """
        To enable the rotting behavior, the following must be present:

        * Stage-like model (linked by '_track_duration_field') must have a 'rotting_threshold_days' integer field
            modeling the number of days before a record rots

        * Model inheriting from duration mixin must have a 'date_last_stage_update' field tracking the last stage change


        Also consider overriding _get_rotting_depends_fields() and _get_rotting_domain().

        Certain views have access to widgets to display rotting status:
            'rotting' for kanbans, 'rotting_statusbar_duration' for forms, 'rotting' for lists.

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
        model_depends = [fname for fname in self._get_rotting_depends_fields() if '.' not in fname]
        self.flush_model(model_depends)  # flush fields to make sure DB is up to date
        self.env[self[self._track_duration_field]._name].flush_model(['rotting_threshold_days'])
        base_query = self._search(self._get_rotting_domain())

        # Our query needs to JOIN the stage field's table.
        # This JOIN needs to use the same alias as the base query to avoid non-matching alias issues
        # Note that query objects do not make their alias table available trivially,
        # but the alias can be inferred by consulting the _joins attribute and compare it to the result of make_alias()
        stage_table_alias_name = base_query.make_alias(self._table, self._track_duration_field)

        # We only need to add a JOIN if the stage table is not already present in the query's _joins attribute.
        from_add_join = ''
        if not base_query._joins or not stage_table_alias_name in base_query._joins:
            from_add_join = """
                INNER JOIN %(stage_table)s AS %(stage_table_alias_name)s
                    ON %(stage_table_alias_name)s.id = %(table)s.%(stage_field)s
            """

        # Items with a date_last_stage_update inferior to that number of months will not be returned by the search function.
        max_rotting_months = self.env['ir.config_parameter'].sudo().get_int('crm.lead.rot.max.months') or 12

        # We use a F-string so that the from_add_join is added with its %s parameters before the query string is processed
        query = f"""
            WITH perishables AS (
                SELECT  %(table)s.id AS id,
                        (
                            %(table)s.date_last_stage_update + %(stage_table_alias_name)s.rotting_threshold_days * interval '1 day'
                        ) AS date_rot
                FROM %(from_clause)s
                    {from_add_join}
                WHERE
                    %(table)s.date_last_stage_update > %(today)s - INTERVAL '%(max_rotting_months)s months'
                    AND %(where_clause)s
            )
            SELECT id
            FROM perishables
            WHERE %(today)s >= date_rot

        """
        self.env.cr.execute(SQL(query,
            table=SQL.identifier(self._table),
            stage_table=SQL.identifier(self[self._track_duration_field]._table),
            stage_table_alias_name=SQL.identifier(stage_table_alias_name),
            stage_field=SQL.identifier(self._track_duration_field),
            today=self.env.cr.now(),
            where_clause=base_query.where_clause,
            from_clause=base_query.from_clause,
            max_rotting_months=max_rotting_months,
        ))
        rows = self.env.cr.dictfetchall()
        return [('id', operator, [r['id'] for r in rows])]
