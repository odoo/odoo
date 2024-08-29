# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import hr

from odoo import fields, models


class HrEmployee(models.Model, hr.HrEmployee):

    hourly_cost = fields.Monetary('Hourly Cost', currency_field='currency_id',
        groups="hr.group_hr_user", default=0.0)
