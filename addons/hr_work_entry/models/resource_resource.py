# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    def _get_sub_leave_domain(self):
        return [('calendar_id', 'in', [False] + self.calendar_id.ids)]

    def _get_leave_domain(self, start_dt, end_dt):
        domain = [
            ('resource_id', 'in', [False] + self.ids),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
            ('company_id', 'in', [False] + self.company_id.ids),
        ]
        return expression.AND([domain, self._get_sub_leave_domain()])

    def _get_resource_calendar_leaves(self, start_dt, end_dt):
        return self.env['resource.calendar.leaves'].search(self._get_leave_domain(start_dt, end_dt))
