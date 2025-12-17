import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

L10N_DK_FIK_MODELS = ('dk_fik_71', 'dk_fik_75')


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(
        selection_add=[
            ('dk_fik_71', "Denmark FIK Number (+71)"),
            ('dk_fik_75', "Denmark FIK Number (+75)"),
        ],
        ondelete={
            'dk_fik_71': lambda recs: recs.write({'invoice_reference_model': 'odoo'}),
            'dk_fik_75': lambda recs: recs.write({'invoice_reference_model': 'odoo'}),
        },
    )

    l10n_dk_fik_creditor_number = fields.Char(
        string="FIK Creditor Number",
        compute='_compute_l10n_dk_fik_creditor_number',
        store=True,
        readonly=False,
    )

    @api.depends('invoice_reference_model', 'company_id.bank_ids.acc_number')
    def _compute_l10n_dk_fik_creditor_number(self):
        for journal in self:
            if journal.invoice_reference_model not in L10N_DK_FIK_MODELS:
                journal.l10n_dk_fik_creditor_number = False
                continue

            bank = journal.company_id.bank_ids[:1]
            creditor_number = '00000000'
            if bank and bank.acc_number:
                digits = re.sub(r'\D', '', bank.acc_number or '')
                creditor_number = digits[-8:].zfill(8)

            journal.l10n_dk_fik_creditor_number = creditor_number

    @api.constrains('l10n_dk_fik_creditor_number', 'invoice_reference_model')
    def _check_fik_creditor_number(self):
        for record in self:
            if record.invoice_reference_model not in L10N_DK_FIK_MODELS:
                continue

            creditor = record.l10n_dk_fik_creditor_number
            if not creditor or not (creditor.isdigit() and len(creditor) == 8):
                raise ValidationError(_("FIK Creditor Number must be exactly 8 digits."))
