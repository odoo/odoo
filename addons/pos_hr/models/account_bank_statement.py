# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import point_of_sale


class AccountBankStatementLine(point_of_sale.AccountBankStatementLine):

    employee_id = fields.Many2one('hr.employee', string="Employee", help="The employee who made the cash move.")
