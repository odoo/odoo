# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nAuSuperAccount(models.Model):
    _name = "l10n_au.super.account"
    _description = "Super Account"

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    display_name = fields.Char(related="employee_id.name", string='Employee Name')
    employee_tfn = fields.Char(related="employee_id.l10n_au_tfn", string='TFN')
    fund_id = fields.Many2one("l10n_au.super.fund", string="Super Fund", required=True)
    fund_type = fields.Selection(related="fund_id.fund_type")
    fund_abn = fields.Char(related="fund_id.abn", string='Fund ABN')
    member_nbr = fields.Char(string='Member Number')
    trustee = fields.Selection([
        ("employee", "The Employee"),
        ("other", "Someone Else"),
    ], string="Trustee")
    trustee_name_id = fields.Many2one("res.partner", string='Trustee Name')
    date_from = fields.Date(string="Effective from", default=lambda self: fields.Date.today())
