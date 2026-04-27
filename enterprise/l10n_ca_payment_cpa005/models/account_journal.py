# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ca_cpa005_destination_data_center = fields.Char(
        "Destination Data Center",
        size=5,
        copy=False,
        help="5-digit ID provided by your bank. It is needed for generating a Canadian EFT file (CPA 005).",
    )
    l10n_ca_cpa005_originator_id = fields.Char(
        "Originator ID",
        size=10,
        copy=False,
        help="10-digit code supplied by your bank. It is needed for generating a Canadian EFT file (CPA 005).",
    )
    l10n_ca_cpa005_fcn_sequence_id = fields.Many2one(
        "ir.sequence",
        "File Creation Number Sequence",
        copy=False,
        help="This is used when generating the File Creation Number for Canadian EFT files. The referenced sequence can "
        "be customized to suit the banks requirements.",
    )
    l10n_ca_cpa005_fcn_number_next = fields.Integer(
        "Next File Creation Number (FCN)",
        compute="_compute_l10n_ca_cpa005_fcn_number_next",
        inverse="_set_l10n_ca_cpa005_fcn_next_number",
        help="Next File Creation Number (FCN) that will be used when validating a Canadian EFT batch payment.The FCN is "
        "a 4-digit sequence from 0001 to 9999. If you need to adjust any details of the FCN go to Sequences in the Technical "
        "menu to adjust them.",
    )

    @api.depends("l10n_ca_cpa005_fcn_sequence_id.number_next_actual")
    def _compute_l10n_ca_cpa005_fcn_number_next(self):
        for journal in self:
            journal._l10n_ca_cpa005_create_sequence_if_needed()
            journal.l10n_ca_cpa005_fcn_number_next = self._l10n_ca_cpa005_modulo_file_creation_number(
                journal.l10n_ca_cpa005_fcn_sequence_id.number_next_actual
            )

    def _set_l10n_ca_cpa005_fcn_next_number(self):
        for journal in self:
            journal._l10n_ca_cpa005_create_sequence_if_needed()
            journal.l10n_ca_cpa005_fcn_sequence_id.sudo().number_next_actual = journal.l10n_ca_cpa005_fcn_number_next

    def _l10n_ca_cpa005_modulo_file_creation_number(self, number):
        """Modulo number to be in 1 <= number <= 9999. 0 is skipped because 0000 is not a valid FCN."""
        return (number - 1) % 9999 + 1

    def _l10n_ca_cpa005_create_sequence_if_needed(self):
        if not self.l10n_ca_cpa005_fcn_sequence_id and "cpa005" in self.outbound_payment_method_line_ids.mapped("code"):
            vals = {
                "name": f"Canadian EFT File Creation Number (FCN) for journal {self.name}",
                "company_id": self.company_id.id,
            }
            self.l10n_ca_cpa005_fcn_sequence_id = self.env["ir.sequence"].sudo().create(vals)

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available("cpa005"):
            res |= self.env.ref("l10n_ca_payment_cpa005.account_payment_method_cpa005")
        return res

    def _l10n_ca_cpa005_next_file_creation_nr(self):
        self._l10n_ca_cpa005_create_sequence_if_needed()
        next_fcn = int(self.l10n_ca_cpa005_fcn_sequence_id.next_by_id())
        return f"{self._l10n_ca_cpa005_modulo_file_creation_number(next_fcn):04}"
