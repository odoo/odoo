# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10nAuSuperFund(models.Model):
    _inherit = "l10n_au.super.fund"

    bank_account_id = fields.Many2one(
        "res.partner.bank",
        string="Bank Account",
        compute="_compute_bank_account",
        store="True", readonly=False,
        domain="[('partner_id', '=', address_id)]",
        help="Bank Account to used for Super Payments to SMSF."
    )

    @api.constrains("bank_account_id", "fund_type")
    def _check_bank_account_id(self):
        for record in self:
            if record.fund_type == "SMSF" and not record.bank_account_id:
                raise ValueError("Bank Account is required for SMSF")
            if record.fund_type == "SMSF" and not record.bank_account_id.aba_bsb:
                raise ValueError("BSB is required for Bank Account for SMSF.")

    @api.depends('address_id', 'address_id.bank_ids')
    def _compute_bank_account(self):
        for rec in self:
            bank_accounts = rec.address_id.sudo().bank_ids
            rec.bank_account_id = bank_accounts[:1]
