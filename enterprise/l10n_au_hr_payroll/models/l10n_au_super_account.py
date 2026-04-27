# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class L10nAuSuperAccount(models.Model):
    _name = "l10n_au.super.account"
    _description = "Super Account"
    _rec_names_search = ["employee_id", "fund_id"]

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    display_name = fields.Char(compute="_compute_display_name", search="_search_display_name", export_string_translation=False)
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
    date_from = fields.Date(string="Member Since", default=lambda self: fields.Date.today(), required=True)
    proportion = fields.Float("Proportion", default=1)
    account_active = fields.Boolean("Active", default=True)
    super_account_warning = fields.Text(related="employee_id.super_account_warning")
    company_id = fields.Many2one('res.company', related='employee_id.company_id', string='Company', store=True)

    _sql_constraints = [
        ('check_proportion',
         'check(proportion >= 0 and proportion <= 1)',
         'The Proportion percentage should be between 0 and 100%')
    ]

    @api.depends('employee_id', 'fund_id')
    def _compute_display_name(self):
        for account in self:
            account.display_name = _("%(emp)s (%(fund)s)", emp=account.employee_id.name, fund=account.fund_id.display_name)
