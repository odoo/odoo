# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import sale_project, hr_timesheet


class ResConfigSettings(sale_project.ResConfigSettings, hr_timesheet.ResConfigSettings):

    invoice_policy = fields.Boolean(string="Invoice Policy", help="Timesheets taken when invoicing time spent")
