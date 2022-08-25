# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class KarmaTracking(models.Model):
    _name = 'gamification.karma.tracking'
    _description = 'Track Karma Changes'
    _rec_name = 'user_id'
    _order = 'tracking_date DESC'

    user_id = fields.Many2one('res.users', 'User', index=True, readonly=True, required=True, ondelete='cascade')
    old_value = fields.Integer('Old Karma Value', required=True, readonly=True)
    new_value = fields.Integer('New Karma Value', required=True, readonly=True)
    consolidated = fields.Boolean('Consolidated')
    tracking_date = fields.Date(default=fields.Date.context_today)

    @api.model
    def _consolidate_last_month(self):
        """ Consolidate last month. Used by a cron to cleanup tracking records. """
        previous_month_start = fields.Date.today() + relativedelta(months=-1, day=1)
        return self._process_consolidate(previous_month_start)

    def _process_consolidate(self, from_date):
        """ Consolidate trackings into a single record for a given month, starting
        at a from_date (included). End date is set to last day of current month
        using a smart calendar.monthrange construction. """
        end_date = from_date + relativedelta(day=calendar.monthrange(from_date.year, from_date.month)[1])
        select_query = """
SELECT user_id,
(
    SELECT old_value from gamification_karma_tracking old_tracking
    WHERE old_tracking.user_id = gamification_karma_tracking.user_id
        AND tracking_date::timestamp BETWEEN %(from_date)s AND %(to_date)s
        AND consolidated IS NOT TRUE
        ORDER BY tracking_date ASC LIMIT 1
), (
    SELECT new_value from gamification_karma_tracking new_tracking
    WHERE new_tracking.user_id = gamification_karma_tracking.user_id
        AND tracking_date::timestamp BETWEEN %(from_date)s AND %(to_date)s
        AND consolidated IS NOT TRUE
        ORDER BY tracking_date DESC LIMIT 1
)
FROM gamification_karma_tracking
WHERE tracking_date::timestamp BETWEEN %(from_date)s AND %(to_date)s
AND consolidated IS NOT TRUE
GROUP BY user_id """
        self.env.cr.execute(select_query, {
            'from_date': from_date,
            'to_date': end_date,
        })
        results = self.env.cr.dictfetchall()
        if results:
            for result in results:
                result['consolidated'] = True
                result['tracking_date'] = fields.Date.to_string(from_date)
            self.create(results)

            self.search([
                ('tracking_date', '>=', from_date),
                ('tracking_date', '<=', end_date),
                ('consolidated', '!=', True)]
            ).unlink()
        return True
