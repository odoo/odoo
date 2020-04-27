# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from dateutil.relativedelta import relativedelta

from odoo.tools import date_utils
from odoo import api, fields, models, _


class KarmaTracking(models.Model):
    _name = 'gamification.karma.tracking'
    _description = 'Track Karma Changes'
    _rec_name = 'user_id'
    _order = 'tracking_date desc, id desc'

    user_id = fields.Many2one('res.users', 'User', index=True, required=True, ondelete='cascade')
    old_value = fields.Integer('Old Karma Value', compute='_compute_old_value', store=True, group_operator="min")
    new_value = fields.Integer('New Karma Value', required=True, group_operator="max")
    consolidated = fields.Boolean('Consolidated')
    # tracking_date is used as create_date would not make the job (take another date as the current date and time)
    # when creating the monthly consolidated data. id of the record will be jointly used as milliseconds are not stored
    # in Datetime fields
    tracking_date = fields.Datetime(default=fields.Datetime.now, readonly=True, index=True)
    reason = fields.Text(default='')
    originated_by = fields.Text(compute='_compute_originated_by', store=True)
    origin_type = fields.Selection([('manual', 'Manual entry')], compute='_compute_origin_type', default="manual", store=True)

    @api.depends('user_id')
    def _compute_old_value(self):
        for karma_tracking in self:
            if karma_tracking.consolidated:
                continue
            search_criteria = [('user_id', '=', karma_tracking.user_id.id)]
            if not isinstance(karma_tracking.id, models.NewId):
                search_criteria += ('|', ('tracking_date', '<', karma_tracking.tracking_date), ('id', '<', karma_tracking.id))
            most_recent_value = self.env['gamification.karma.tracking'].search(search_criteria, order="tracking_date desc, id desc", limit=1)
            karma_tracking.old_value = most_recent_value[0].new_value if most_recent_value else 0

    def _compute_origin_type(self):
        for karma_tracking in self:
            karma_tracking.origin_type = 'manual'

    def _compute_originated_by(self):
        for karma_tracking in self:
            karma_tracking.originated_by = ''

    @api.model
    def _consolidate_old_karma_tracking(self):
        """ Consolidate data from 2 month ago (so that we keep the detail (origin and reason) at least one month).
        Used by a cron to cleanup tracking records."""
        month_to_process_date = fields.Date.today() + relativedelta(months=-2)
        return self._process_consolidate_monthly_data(month_to_process_date)

    @api.model
    def _process_consolidate_monthly_data(self, from_date):
        """ Consolidate trackings into a single record for a given month. Starting
        date is recomputed to ensure we start at the first day of the month at 00:00.
        End date is set to last day of current month, a millisecond before next month. """
        from_date = date_utils.start_of(from_date, "month").date()
        to_date = date_utils.end_of(from_date, "month") + relativedelta(days=1, microseconds=-1)
        select_query = """
  SELECT DISTINCT user_id,
		  FIRST_VALUE(old_value) OVER W_PARTITION as old_value,
		  LAST_VALUE(new_value) OVER W_PARTITION as new_value,
		  FIRST_VALUE(tracking_date) OVER W_PARTITION as from_tracking_date,
		  LAST_VALUE(tracking_date) OVER W_PARTITION as to_tracking_date
    FROM gamification_karma_tracking
   WHERE tracking_date BETWEEN %(from_date)s AND %(to_date)s AND consolidated IS NOT TRUE
  WINDOW W_PARTITION AS (PARTITION BY user_id ORDER BY tracking_date, id RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)"""
        self.env.cr.execute(select_query, {
            'from_date': from_date,
            'to_date': to_date,
        })
        results = self.env.cr.dictfetchall()
        if results:
            for result in results:
                from_tracking_date = result.pop('from_tracking_date')
                to_tracking_date = result.pop('to_tracking_date')
                result['consolidated'] = True
                # Using latest tracking date prevents having tracking_date duplicates in case this method
                # is called several times on the current ongoing month (although this is not the intended use
                # of this method).
                result['tracking_date'] = to_tracking_date
                result['reason'] = _('Consolidation from %s to %s') % (from_tracking_date.strftime("%Y-%m-%m %H:%M:%S"), to_tracking_date.strftime("%Y-%m-%m %H:%M:%S"))
            self.create(results)

            self.search([
                ('tracking_date', '>=', from_date),
                ('tracking_date', '<=', to_date),
                ('consolidated', '!=', True)]
            ).unlink()
        return True

    @api.model
    def create_karma_tracking_dict(self, user_id, old_karma_value, new_karma_value, source=None, reason=''):
        """
        Prepare the dict of values to create the new karma tracking.

        :param user_id: id of the user the karma tracking is related to
        :param old_karma_value: old karma value
        :param new_karma_value: new karma value
        :param source: source of the karma change (either a slide.channel or a forum.post)
        :param reason: reason of the karma change
        """
        karma_tracking = {
            'user_id': user_id,
            'old_value': old_karma_value,
            'new_value': new_karma_value,
            'reason': reason
        }
        if source:
            if 'slide.slide' in self.env and isinstance(source, type(self.env['slide.slide'])):
                karma_tracking['originated_by_slide_id'] = source.id
            elif 'slide.channel' in self.env and isinstance(source, type(self.env['slide.channel'])):
                karma_tracking['originated_by_slide_channel_id'] = source.id
            elif 'forum.post' in self.env and isinstance(source, type(self.env['forum.post'])):
                karma_tracking['originated_by_post_id'] = source.id
        return karma_tracking
