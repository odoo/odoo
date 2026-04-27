from odoo import api, fields, models, _
from .hr_employee import CANTONS

class l10nCHISMutation(models.Model):
    _name = "l10n.ch.is.mutation"
    _description = "Source-Tax Mutations"
    _order = "valid_as_of desc"

    employee_snapshot_id = fields.Many2one("l10n.ch.employee.monthly.values")
    employee_id = fields.Many2one("hr.employee")
    qst_canton = fields.Selection(selection=CANTONS, string="Canton")
    qst_municipality = fields.Char(string="Municipality")
    reason = fields.Selection(selection=[("entryCompany", "Entry : Entry In Company"),
                                         ("entryCanton", "Entry: Canton Change"),
                                         ("entryOther", "Entry: Other"),
                                         ("withdrawalCompany", "Withdrawal: Withdrawal From Company"),
                                         ("withdrawalNat", "Withdrawal : Naturalisation"),
                                         ("withdrawalSettled", "Withdrawal: C-Permit"),
                                         ("withdrawalCanton", "Withdrawal: Canton Change"),
                                         ("withdrawalOther", "Withdrawal: Other"),
                                         ("civilstate", "Mutation : Civil Status"),
                                         ("partnerWork", "Mutation : Partner's Work"),
                                         ("partnerWorkplaceChangeCHAbroad", "Mutation : Partner Workplace CH/EX"),
                                         ("residence", "Mutation : Residence"),
                                         ("childrenDeduction", "Mutation : Children Deduction"),
                                         ("churchTax", "Mutation : Church Tax"),
                                         ("others", "Mutation : Other")], required=True)
    valid_as_of = fields.Date(required=True)
    is_correction_id = fields.Many2one("hr.employee.is.line", ondelete="cascade")
    auto_generated = fields.Boolean()
