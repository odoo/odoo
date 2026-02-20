import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(
        selection_add=[('dk_fik', 'Denmark FIK Number')],
        ondelete={'dk_fik': lambda recs: recs.write({'invoice_reference_model': 'odoo'})}
    )

    l10n_dk_fik_creditor_number = fields.Char(
        string="FIK Creditor Number",
        compute="_compute_l10n_dk_fik_creditor_number",
        store=True,
        readonly=False
    )

    @api.depends('invoice_reference_model', 'company_id.bank_ids.acc_number')
    def _compute_l10n_dk_fik_creditor_number(self):
        for journal in self:
            # Only compute when FIK is selected
            if journal.invoice_reference_model != 'dk_fik':
                continue

            creditor_number = "00000000"
            bank = journal.company_id.bank_ids[:1]
            if bank.acc_number:
                digits = re.sub(r"\D", "", bank.acc_number)
                creditor_number = digits[-8:].zfill(8)  # The creditor number must be 8 digits.

            journal.l10n_dk_fik_creditor_number = creditor_number

    @api.constrains('l10n_dk_fik_creditor_number', 'invoice_reference_model')
    def _check_fik_creditor_number(self):
        for record in self:
            if record.invoice_reference_model != 'dk_fik':
                continue
            creditor = record.l10n_dk_fik_creditor_number
            if not creditor or not (creditor.isdigit() and len(creditor) == 8):
                raise ValidationError(
                    "FIK Creditor Number must be exactly 8 digits."
                )
