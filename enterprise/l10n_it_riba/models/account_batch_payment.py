import base64

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from odoo.addons.l10n_it_riba.tools.riba import file_export


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def _get_methods_generating_files(self):
        return (super()._get_methods_generating_files() or []) + ['riba']

    def _l10n_it_riba_check(self):
        errors = []
        if self.batch_type != 'inbound':
            errors.append(_("Batch payment type must be inbound."))
        if not self.journal_id.company_id.l10n_it_sia_code:
            errors.append(_("Company '%s' must have a SIA code.", self.journal_id.company_id.name))
        bank_account = self.journal_id.bank_account_id
        if not bank_account:
            errors.append(_("Journal '%s' has no associated bank account.", self.journal_id.name))
        elif (not bank_account.acc_number or bank_account.acc_type != 'iban'):
            errors.append(_("The bank account associated with the journal '%s' has no IBAN.", self.journal_id.name))
        elif bank_account.acc_number[:2] != 'IT':
            errors.append(_("Only bank accounts with an Italian IBAN are allowed to use Ri.Ba. payments"))
        errors += self.payment_ids._l10n_it_riba_check()
        return errors

    def _generate_export_file(self):
        if self.payment_method_code != 'riba':
            return super()._generate_export_file()

        errors = self._l10n_it_riba_check()
        if errors:
            raise UserError("\n".join(errors))

        values = self._l10n_it_riba_get_values()
        content = file_export(values)
        return {
            'filename': f"riba_{self.name.replace('/', '_')}_{fields.Datetime.now():%Y%m%d_%H%M%S}.txt",
            'file': base64.encodebytes(content.encode())
        }

    def _l10n_it_riba_get_values(self):
        amount = self.amount * 100
        abs_rounded_amount = int(float_round(abs(amount), 0))
        creditor = self.journal_id.company_id
        creditor_bank_account = self.journal_id.bank_account_id
        creditor_bank = self.journal_id.bank_id

        common = {
            'creditor_sia_code': creditor.l10n_it_sia_code,
            'creditor_abi': creditor_bank_account.get_iban_part("bank"),
            'support_name': self.name,
        }

        records = (
            [{'record_type': 'IB', **common}]
            + self.payment_ids._l10n_it_riba_get_values(creditor, creditor_bank, creditor_bank_account)
            + [{
                'record_type': 'EF',
                **common,
                'n_sections': len(self.payment_ids),
                'negative_total': abs_rounded_amount if amount > 0.0 else 0,
                'positive_total': abs_rounded_amount if amount < 0.0 else 0,
            }]
        )
        records[-1]['n_records'] = len(records)
        return records
