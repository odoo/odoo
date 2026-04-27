import re

from odoo import _, api, models
from odoo.tools.float_utils import float_round


def spaced_join(*args):
    return " ".join([x for x in args if x])


def fiscal_code(partner):
    return partner._l10n_it_edi_get_values()['codice_fiscale']


def accents_to_apostrophes(s):
    if s and set("áàèéìíóòùúÁÀÈÉÌÍÓÒÙÚ") ^ set(s):
        s = re.sub('[áà]', "a'", s)
        s = re.sub('[èé]', "e'", s)
        s = re.sub('[ìí]', "i'", s)
        s = re.sub('[óò]', "o'", s)
        s = re.sub('[ùú]', "u'", s)
        s = re.sub('[ÁÀ]', "A'", s)
        s = re.sub('[ÈÉ]', "E'", s)
        s = re.sub('[ÌÍ]', "I'", s)
        s = re.sub('[ÓÒ]', "O'", s)
        s = re.sub('[ÙÚ]', "U'", s)
    return s


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _l10n_it_riba_check(self):
        errors = []
        partner2bank_accounts = self.env['res.partner.bank'].search([('partner_id', 'in', self.partner_id.ids)]).grouped('partner_id')
        for payment in self:
            partner_bank_account = partner2bank_accounts.get(payment.partner_id, self.env['res.partner.bank'])[:1]
            if not partner_bank_account:
                errors.append(_("Partner '%s' has no bank account.", payment.partner_id.display_name))
            elif (not partner_bank_account.acc_number or partner_bank_account.acc_type != 'iban'):
                errors.append(_("The bank account associated with the partner '%s' has no IBAN.", payment.partner_id.name))
            elif partner_bank_account.acc_number[:2] != 'IT':
                errors.append(_("Only bank accounts with an Italian IBAN are allowed to use Ri.Ba. payments"))
            if not fiscal_code(payment.partner_id):
                errors.append(_("Partner '%s' must have a Codice Fiscale", payment.partner_id.name))
            if payment.currency_id.name != 'EUR':
                errors.append(_("Only EUR can be used as currency in Ri.Ba. payments, not %s", payment.currency_id.name))
        return errors

    @api.model
    def _get_method_codes_using_bank_account(self):
        return (super()._get_method_codes_using_bank_account() or []) + ['riba']

    @api.model
    def _get_method_codes_needing_bank_account(self):
        return (super()._get_method_codes_needing_bank_account() or []) + ['riba']

    def _l10n_it_riba_get_values(self, creditor, creditor_bank, creditor_bank_account):
        records = []
        partner2bank_accounts = self.env['res.partner.bank'].search([('partner_id', 'in', self.partner_id.ids)]).grouped('partner_id')
        for section_number, payment in enumerate(self, 1):
            partner = payment.partner_id
            company_partner = payment.company_id.partner_id
            debitor_bank_account = partner2bank_accounts.get(payment.partner_id, self.env['res.partner.bank'])[:1]
            rounded_amount = payment.currency_id.round(payment.amount)
            reconciled_invoices = payment.reconciled_invoice_ids
            records += [
                {
                    'record_type': '14',  # Disposition
                    'section_number': section_number,
                    'payment_date': payment.date,
                    'amount': int(float_round(rounded_amount * 100, 0)),
                    'creditor_abi': creditor_bank_account.get_iban_part("bank"),
                    'creditor_cab': creditor_bank_account.get_iban_part("branch"),
                    'creditor_ccn': creditor_bank_account.get_iban_part("account"),
                    'debitor_abi': debitor_bank_account.get_iban_part("bank"),
                    'debitor_cab': debitor_bank_account.get_iban_part("branch"),
                    'creditor_sia_code': payment.company_id.l10n_it_sia_code,
                    'debitor_code': partner.ref or partner.name,
                }, {
                    'record_type': '20',  # Creditor description
                    'section_number': section_number,
                    'segment_1': accents_to_apostrophes(company_partner.display_name),
                    'segment_2': spaced_join(company_partner.street, company_partner.street2),
                    'segment_3': company_partner.city,
                    'segment_4': spaced_join(company_partner.ref, company_partner.phone or company_partner.mobile or company_partner.email),
                }, {
                    'record_type': '30',  # Debitor description
                    'section_number': section_number,
                    'segment_1': accents_to_apostrophes(partner.display_name),
                    'debitor_tax_code': fiscal_code(partner),
                }, {
                    'record_type': '40',  # Debitor address
                    'section_number': section_number,
                    'debitor_address': spaced_join(partner.street, partner.street2),
                    'debitor_zip': partner.zip,
                    'debitor_city': partner.city,
                    'debitor_state': partner.state_id.code,
                    'debitor_bank_name': accents_to_apostrophes(debitor_bank_account.bank_id.display_name),
                }, {
                    'record_type': '50',  # Creditor address
                    'section_number': section_number,
                    'segment_1': spaced_join(
                        payment.move_id.l10n_it_cig,
                        payment.move_id.l10n_it_cup,
                        payment.memo or spaced_join(_("Invoice"), *reconciled_invoices.mapped("name")),
                        _("Amount"),
                        f"{rounded_amount:0.2f}",
                    ),
                    'creditor_tax_code': fiscal_code(company_partner),
                }, {
                    'record_type': '51',  # Creditor information
                    'section_number': section_number,
                    'receipt_number': payment.id % 10 ** 10,
                    'creditor_name': accents_to_apostrophes(company_partner.display_name),
                }, {
                    'record_type': '70',  # Summary
                    'section_number': section_number,
                },
            ]
        return records
