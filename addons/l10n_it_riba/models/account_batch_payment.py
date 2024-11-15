import base64

from odoo import _, models
from odoo.addons.l10n_it_riba.tools.riba import file_export, RibaValues


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def _get_methods_generating_files(self):
        return (super()._get_methods_generating_files() or []) + ['riba']

    def _l10n_it_riba_check(self):
        """
        CHECKS:
            "No SIA Code specified for %(company)s"
            "No IBAN specified for %(company)s."
            "No VAT or Fiscal Code specified for %(company)s",
        """
        return (
            self.batch_type == 'inbound'
            and not self.is_internal_transfer
            and all(payment._l10n_it_riba_check() for payment in self.payment_ids)
        )

    def _generate_export_file(self):
        if self.payment_method_code == 'riba':
            if not self._l10n_it_riba_check():
                raise ValueError("Invalid RIBA export")
            values = self._l10n_it_riba_get_values()
            content = file_export(values)
            return {
                'filename': f"riba_{self.name}.txt",
                'file': base64.encodebytes(content)
            }
        else:
            return super()._generate_export_file()

    def _l10n_it_riba_get_values(self):
        creditor = self.journal_id.company_id
        creditor_bank_account = self.journal_id.bank_account_id
        creditor_bank = self.journal_id.bank_id
        amount = sum(payment.amount_signed for payment in self.payment_ids)
        sections = [payment._l10n_it_riba_get_values(
            idx,
            creditor,
            creditor_bank,
            creditor_bank_account
        ) for idx, payment in enumerate(self.payment_ids)]
        n_records = 2 + sum(len(section) for section in sections)
        header = {
            'creditor_sia_code': creditor.l10n_it_sia_code,
            'creditor_abi': creditor_bank.l10n_it_abi,
            'support_name': self.name,
        }
        footer = {
            **header,
            'n_sections': len(self.payment_ids),
            'negative_total': amount if amount < 0.0 else 0.0,
            'positive_total': amount if amount > 0.0 else 0.0,
            'n_records': n_records,
        }
        return RibaValues(header=header, sections=sections, footer=footer)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _l10n_it_riba_check(self):
        """
            "No IBAN or ABI/CAB specified for %(partner)s",
            "No VAT or Fiscal Code specified for %(partner)s",
        """
        return True

    def _l10n_it_riba_get_next_sequence_number(self):
        """ Get the next number from the Riba sequence for the company.
            If it doesn't exist, create it.
        """
        company = self.journal_id.company_id
        if number := self.env['ir.sequence'].with_company(company).next_by_code('l10n_it_riba.riba_sequence'):
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'Ri.Ba. Sequence',
                'code': 'l10n_it_riba.riba_sequence',
                'company_id': company.id,
                'number_next': 1,
            })
            number = sequence._next()
        # The number is returned as a string, but we require an int
        return int(''.join(filter(lambda c: c.isdecimal(), number)))

    def _l10n_it_riba_get_values(self, section_number, creditor, creditor_bank, creditor_bank_account):

        partner = self.partner_id
        company_partner = self.company_id.partner_id
        partner_bank = self.env['res_partner_bank'].search([('partner_id', '=', partner.id)], limit=1)[:1]
        debitor_bank = partner_bank or self.env['res.bank']
        receipt_number = self._l10n_it_riba_get_next_sequence_number()

        def spaced_join(*args):
            return " ".join([x for x in args if x])
        def fiscal_code(partner):
            return partner._l10n_it_normalize_codice_fiscale(partner.l10n_it_codice_fiscale)

        return [
            {
                'record_type': '14',
                'section_number': section_number,
                'payment_date': self.date_maturity,
                'amount': self.amount,
                'creditor_abi': creditor_bank.l10n_it_abi,
                'creditor_cab': creditor_bank.l10n_it_cab,
                'creditor_ccn': creditor_bank.l10n_it_ccn,
                'debitor_abi': debitor_bank.l10n_it_abi,
                'debitor_cab': debitor_bank.l10n_it_cab,
                'creditor_sia_code': creditor._l10n_it_sia_code,
                'debitor_code': partner.ref or partner.name,
            },
            {
                'record_type': '20',
                'section_number': section_number,
                'segment_1': company_partner.display_name,
                'segment_2': spaced_join(company_partner.street, company_partner.street2),
                'segment_3': spaced_join(company_partner.zip, company_partner.city),
                'segment_4': spaced_join(company_partner.ref, company_partner.phone or company_partner.mobile or company_partner.email),
            },
            {
                'record_type': '30',
                'section_number': section_number,
                'segment_1': partner.display_name,
                'debitor_tax_code': fiscal_code(partner),
            },
            {
                'record_type': '40',
                'section_number': section_number,
                'debitor_address': spaced_join(partner.street, partner.street2),
                'debitor_zip': partner.zip,
                'debitor_city': partner.city,
                'debitor_state': partner.state.code,
                'debitor_bank_name': debitor_bank.display_name,
            },
            {
                'record_type': '50',
                'section_number': section_number,
                'segment_1': spaced_join(
                    self.move_id.l10n_it_cig,
                    self.move_id.l10n_it_cup,
                    _("Invoice"),
                    self.move_id.name,
                    f"{self.move_id.date:%Y%m%d}",
                    _("Amount"),
                    f"{self.amount:0.2f}",
                ),
                'creditor_tax_code': fiscal_code(company_partner),
            },
            {
                'record_type': '51',
                'section_number': section_number,
                'receipt_number': receipt_number,
                'creditor_name': company_partner.display_name,
            },
            {
                'record_type': '70',
                'section_number': section_number,
            },
        ]
