# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import models, fields
from odoo.osv import expression


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    def _get_sub_leave_domain(self):
        domain = super()._get_sub_leave_domain()
        return expression.OR([
            domain,
            [('holiday_id.employee_id', 'in', self.employee_id.ids)] # see https://github.com/odoo/enterprise/pull/15091
        ])
