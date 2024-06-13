# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import date_utils


class KarmaTracking(models.Model):
    _name = 'gamification.karma.tracking'
    _description = 'Track Karma Changes'
    _rec_name = 'user_id'
    _order = 'tracking_date desc, id desc'

    def _get_origin_selection_values(self):
        return [('res.users', _('User'))]

    user_id = fields.Many2one('res.users', 'User', index=True, required=True, ondelete='cascade')
    old_value = fields.Integer('Old Karma Value', readonly=True)
    new_value = fields.Integer('New Karma Value', required=True)
    gain = fields.Integer('Gain', compute='_compute_gain', readonly=False)
    consolidated = fields.Boolean('Consolidated')

    tracking_date = fields.Datetime(default=fields.Datetime.now, readonly=True, index=True)
    reason = fields.Text(default=lambda self: _('Add Manually'), string='Description')
    origin_ref = fields.Reference(
        string='Source',
        selection=lambda self: self._get_origin_selection_values(),
        default=lambda self: f'res.users,{self.env.user.id}',
    )
    origin_ref_model_name = fields.Selection(
        string='Source Type', selection=lambda self: self._get_origin_selection_values(),
        compute='_compute_origin_ref_model_name', store=True)

    @api.depends('old_value', 'new_value')
    def _compute_gain(self):
        for karma in self:
            karma.gain = karma.new_value - (karma.old_value or 0)

    @api.depends('origin_ref')
    def _compute_origin_ref_model_name(self):
        for karma in self:
            if not karma.origin_ref:
                karma.origin_ref_model_name = False
                continue

            karma.origin_ref_model_name = karma.origin_ref._name

    @api.model_create_multi
    def create(self, values_list):
        # fill missing old value with current user karma
        users = self.env['res.users'].browse([
            values['user_id']
            for values in values_list
            if 'old_value' not in values and values.get('user_id')
        ])
        karma_per_users = {user.id: user.karma for user in users}

        for values in values_list:
            if 'old_value' not in values and values.get('user_id'):
                values['old_value'] = karma_per_users[values['user_id']]

            if 'gain' in values and 'old_value' in values:
                values['new_value'] = values['old_value'] + values['gain']
                del values['gain']

        return super().create(values_list)

    @api.model
    def _consolidate_cron(self):
        """Consolidate the trackings 2 months ago. Used by a cron to cleanup tracking records."""
        from_date = date_utils.start_of(fields.Datetime.today(), 'month') - relativedelta(months=2)
        return self._process_consolidate(from_date)

    def _process_consolidate(self, from_date, end_date=None):
        """Consolidate the karma trackings.

        The consolidation keeps, for each user, the oldest "old_value" and the most recent
        "new_value", creates a new karma tracking with those values and removes all karma
        trackings between those dates. The origin / reason is changed on the consolidated
        records, so this information is lost in the process.
        """
        self.env['gamification.karma.tracking'].flush_model()

        if not end_date:
            end_date = date_utils.end_of(date_utils.end_of(from_date, 'month'), 'day')

        select_query = """
        WITH old_tracking AS (
            SELECT DISTINCT ON (user_id) user_id, old_value, tracking_date
              FROM gamification_karma_tracking
             WHERE tracking_date BETWEEN %(from_date)s
               AND %(end_date)s
               AND consolidated IS NOT TRUE
          ORDER BY user_id, tracking_date ASC, id ASC
        )
            INSERT INTO gamification_karma_tracking (
                            user_id,
                            old_value,
                            new_value,
                            tracking_date,
                            origin_ref,
                            consolidated,
                            reason)
            SELECT DISTINCT ON (nt.user_id)
                            nt.user_id,
                            ot.old_value AS old_value,
                            nt.new_value AS new_value,
                            ot.tracking_date AS from_tracking_date,
                            %(origin_ref)s AS origin_ref,
                            TRUE,
                            %(reason)s
              FROM gamification_karma_tracking AS nt
              JOIN old_tracking AS ot
                   ON ot.user_id = nt.user_id
             WHERE nt.tracking_date BETWEEN %(from_date)s
               AND %(end_date)s
               AND nt.consolidated IS NOT TRUE
          ORDER BY nt.user_id, nt.tracking_date DESC, id DESC
        """

        self.env.cr.execute(select_query, {
            'from_date': from_date,
            'end_date': end_date,
            'origin_ref': f'res.users,{self.env.user.id}',
            'reason': _('Consolidation from %(from_date)s to %(end_date)s', from_date=from_date.date(), end_date=end_date.date()),
        })

        trackings = self.search([
            ('tracking_date', '>=', from_date),
            ('tracking_date', '<=', end_date),
            ('consolidated', '!=', True)]
        )
        # HACK: the unlink() AND the flush_all() must have that key in their context!
        trackings = trackings.with_context(skip_karma_computation=True)
        trackings.unlink()
        trackings.env.flush_all()
        return True
