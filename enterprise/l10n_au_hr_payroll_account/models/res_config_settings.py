# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_au_hr_super_responsible_id = fields.Many2one(
        related="company_id.l10n_au_hr_super_responsible_id", readonly=False
    )
    l10n_au_superstream_payable_account_id = fields.Many2one(
        "account.account",
        "SuperStream Payable Account",
        compute="_compute_super_payable_account",
        inverse="_set_super_payable_account",
        readonly=False,
        groups="hr_payroll.group_hr_payroll_manager"
    )
    l10n_au_previous_bms_id = fields.Char(related="company_id.l10n_au_previous_bms_id", readonly=False)
    l10n_au_bms_id = fields.Char(related='company_id.l10n_au_bms_id', readonly=False)
    l10n_au_stp_responsible_id = fields.Many2one(
        related="company_id.l10n_au_stp_responsible_id", readonly=False)

    @api.depends('company_id')
    def _compute_super_payable_account(self):
        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        for rec in self:
            rec.l10n_au_superstream_payable_account_id = clearing_house.with_company(
                rec.company_id).property_account_payable_id

    def _set_super_payable_account(self):
        clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
        if not clearing_house:
            raise UserError(_("No clearing house record found for this company!"))
        for rec in self:
            clearing_house.with_company(
                rec.company_id).sudo().property_account_payable_id = rec.l10n_au_superstream_payable_account_id
