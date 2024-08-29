# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import account
from odoo import fields, models


class AccountBankStatementLine(models.Model, account.AccountBankStatementLine):

    employee_id = fields.Many2one('hr.employee', string="Employee", help="The employee who made the cash move.")
