# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning


ACCOUNT_TYPE_MAPPING = {
    "regular": "1",
    "current": "2",
    "savings": "4",
    "other": "9",
}


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    l10n_jp_zengin_merge_transactions = fields.Boolean(
        string="Merge Transactions",
        help="Merge collective payments for Zengin files",
        compute="_compute_l10n_jp_zengin_merge_transactions",
        store=True, readonly=False,
    )

    @api.depends('journal_id')
    def _compute_l10n_jp_zengin_merge_transactions(self):
        for record in self:
            record.l10n_jp_zengin_merge_transactions = record.journal_id.l10n_jp_zengin_merge_transactions

    def _validate_bank_account_for_zengin(self, bank_account):
        bank = bank_account.bank_id
        partner = bank_account.partner_id
        bank_error_msgs = []
        bank_account_error_msgs = []

        if not bank.bic:
            bank_error_msgs.append(_("Please set a BIC on the %(bank)s bank.", bank=bank.name))
        if not bank.l10n_jp_zengin_name_kana:
            bank_error_msgs.append(_("Please set a bank name in Kana on the %(bank)s bank.", bank=bank.name))
        if not bank.l10n_jp_zengin_branch_code:
            bank_error_msgs.append(_("Please set a branch code on the %(bank)s bank.", bank=bank.name))
        if not bank.l10n_jp_zengin_branch_name_kana:
            bank_error_msgs.append(_("Please set a branch name in Kana on the %(bank)s bank.", bank=bank.name))
        if not bank_account.l10n_jp_zengin_acc_holder_name_kana:
            bank_account_error_msgs.append(_("Please set an account holder name in Kana on the %(account)s bank account for %(partner)s.", account=bank_account.display_name, partner=partner.display_name))
        if not bank_account.l10n_jp_zengin_account_type:
            bank_account_error_msgs.append(_("Please set an account type on the %(account)s bank account for %(partner)s.", account=bank_account.display_name, partner=partner.display_name))

        if bank_error_msgs:
            action_error = {
                'view_mode': 'form',
                'res_model': 'res.bank',
                'type': 'ir.actions.act_window',
                'res_id': bank.id,
                'views': [[self.env.ref('base.view_res_bank_form').id, 'form']],
            }
            raise RedirectWarning('\n'.join(bank_error_msgs), action_error, _("Go to Bank"))

        if bank_account_error_msgs:
            action_error = {
                'view_mode': 'form',
                'res_model': 'res.partner.bank',
                'type': 'ir.actions.act_window',
                'res_id': bank_account.id,
                'views': [[self.env.ref('base.view_partner_bank_form').id, 'form']],
            }
            raise RedirectWarning('\n'.join(bank_account_error_msgs), action_error, _("Go to Bank Account"))

    def _validate_sender_for_zengin(self):
        journal = self.journal_id
        bank_account = journal.bank_account_id
        self._validate_bank_account_for_zengin(bank_account)

        error_msgs = []
        if not bank_account.l10n_jp_zengin_client_code:
            error_msgs.append(_("Please set a client code on the %(account)s bank account for %(partner)s.", account=bank_account.display_name, partner=bank_account.partner_id.display_name))
        if bank_account.l10n_jp_zengin_account_type == 'savings':
            error_msgs.append(_("Savings account type is not supported for Zengin on %(account)s bank account for %(partner)s.", account=bank_account.display_name, partner=bank_account.partner_id.display_name))

        if error_msgs:
            action_error = {
                'view_mode': 'form',
                'res_model': 'res.partner.bank',
                'type': 'ir.actions.act_window',
                'res_id': bank_account.id,
                'views': [[self.env.ref('base.view_partner_bank_form').id, 'form']],
            }
            raise RedirectWarning('\n'.join(error_msgs), action_error, _("Go to Bank Account"))

    def _generate_zengin_header(self):
        transfer_date = self.date
        journal = self.journal_id
        bank_account = journal.bank_account_id
        bank = journal.bank_id
        return "".join([
            "1",                                                                  # Record type code
            "21",                                                                 # Type code: 21 General transfer
            "0",                                                                  # Code division
            f"{bank_account.l10n_jp_zengin_client_code:10.10}"                    # Company code
            f"{bank_account.l10n_jp_zengin_acc_holder_name_kana:40.40}",          # Name of remittance requester (kana)
            transfer_date.strftime('%m%d'),                                       # Transfer date MMDD
            f"{bank.bic:4.4}",                                                    # Bank code
            f"{bank.l10n_jp_zengin_name_kana:15.15}",                             # Bank name (Kana)
            f"{bank.l10n_jp_zengin_branch_code:3.3}",                             # Branch Code
            f"{bank.l10n_jp_zengin_branch_name_kana:15.15}",                      # Branch name (Kana)
            f"{ACCOUNT_TYPE_MAPPING[bank_account.l10n_jp_zengin_account_type]}",  # Subjects: 1: Regular, 2: Current, 4: Saving, 9: Other
            f"{bank_account.acc_number:7.7}",                                     # Account Number
            f"{'':17}"                                                            # Dummy
        ])

    def _generate_zengin_entry_detail(self, payments):
        bank_account = payments.partner_bank_id
        bank = bank_account.bank_id
        return "".join([
            "2",                                                                    # Record type code
            f"{bank.bic:4.4}",                                                      # Bank code
            f"{bank.l10n_jp_zengin_name_kana:15.15}",                               # Bank name (Kana)
            f"{bank.l10n_jp_zengin_branch_code:3.3}",                               # Branch code
            f"{bank.l10n_jp_zengin_branch_name_kana:15.15}",                        # Branch name (Kana)
            "0000",                                                                 # Clearing house code
            f"{ACCOUNT_TYPE_MAPPING[bank_account.l10n_jp_zengin_account_type]}",    # Subjects: 1: Regular, 2: Current, 4: Saving, 9: Other
            f"{bank_account.acc_number:7.7}",                                       # Account number
            f"{bank_account.l10n_jp_zengin_acc_holder_name_kana:30.30}",            # Name of remittance requester (kana)
            f"{int(sum(payments.mapped('amount'))):0>10d}",                         # Amount
            "0",                                                                    # New Code, 0: Other
            "0000000000"                                                            # Customer code 1
            "0000000000"                                                            # Customer code 2
            "7",                                                                    # Transfer designation category (* Regardless of the transfer category, Web21 will handle it as a "7. telegraphic transfer.)
            " ",                                                                    # Identification code (Optional item therefore can be left blank)
            f"{'':7}"                                                               # Dummy
        ])

    def _generate_zengin_trailer(self, record_count, payments):
        return "".join([
            "8",                                             # Record Type Code
            f"{record_count:0>6d}",                          # Total number of records
            f"{int(sum(payments.mapped('amount'))):0>12d}",  # Total amount
            f"{'':101}"                                      # Dummy
        ])

    def _generate_zengin_footer(self):
        return "".join([
            "9",         # Record Type Code
            f"{'':119}"  # Dummy
        ])

    def _generate_zengin_file(self):
        entries = [self._generate_zengin_header()]

        grouped_payments = self.payment_ids.grouped("partner_bank_id")
        record_count = 0
        for partner_bank_id, payments in grouped_payments.items():
            self._validate_bank_account_for_zengin(partner_bank_id)
            if self.l10n_jp_zengin_merge_transactions:
                entries.append(self._generate_zengin_entry_detail(payments))
                record_count += 1
            else:
                entries.extend([self._generate_zengin_entry_detail(payment) for payment in payments])
                record_count += len(payments)

        entries.extend([
            self._generate_zengin_trailer(record_count, self.payment_ids),
            self._generate_zengin_footer()
        ])

        return "\r\n".join(entries)

    def _get_methods_generating_files(self):
        res = super()._get_methods_generating_files()
        res.append("zengin")
        return res

    def _generate_export_file(self):
        if self.payment_method_code == "zengin":
            self._validate_sender_for_zengin()
            data = self._generate_zengin_file()
            date = fields.Datetime.today().strftime("%Y-%m-%d")  # JP date format
            return {
                "file": base64.encodebytes(data.encode(encoding="Shift_JIS")),
                "filename": f"ZENGIN-{self.journal_id.code}-{date}.txt",
            }
        else:
            return super()._generate_export_file()
