# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import choice
from pytz import timezone, UTC, utc
from datetime import timedelta, datetime
from string import digits

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_time
from odoo.addons.base.models.res_partner import _tz_get

class HrEmployeeVersion(models.Model):
    _inherit = ['hr.employee.version']

    # Employee Fields
    legal_name = fields.Char(related='employee_id.legal_name', store=True, readonly=False)

    # Contract Fields
    contract_name = fields.Char('Contract Reference')
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
