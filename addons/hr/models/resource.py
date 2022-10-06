# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from pytz import utc, timezone
from datetime import datetime

from odoo import fields, models
from odoo.addons.resource.models.resource import Intervals


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many('hr.employee', 'resource_id', domain="[('company_id', '=', company_id)]")
