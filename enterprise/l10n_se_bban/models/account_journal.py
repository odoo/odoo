from lxml import etree

from odoo import api, fields, models
from odoo.tools import float_repr


class AccountJournal(models.Model):
    _inherit = "account.journal"

    has_iso_se_payment_method = fields.Boolean(compute='_compute_has_iso_se_payment_method')

    @api.depends('outbound_payment_method_line_ids.payment_method_id.code')
    def _compute_has_iso_se_payment_method(self):
        for journal in self:
            journal.has_iso_se_payment_method = 'iso20022_se' in journal.outbound_payment_method_line_ids.payment_method_id.mapped('code')

    @api.depends('bank_acc_number', 'company_id.account_fiscal_country_id', 'company_id.country_id')
    def _compute_sepa_pain_version(self):
        se_bban_journals = self.filtered(lambda j: j.bank_account_id.acc_type in ('bban_se', 'plusgiro', 'bankgiro'))
        # For SE BBAN, we use the pain.001.001.03 version
        se_bban_journals.sepa_pain_version = 'pain.001.001.03'
        super(AccountJournal, self - se_bban_journals)._compute_sepa_pain_version()

    # TODO: remove partner_acc_type arg in master
    def _is_se_bban(self, payment_method_code, partner_acc_type=None):
        """ Whenever this journal should be considered as a swedish bban, plusgiro or bankgiro
            in a batch payment.

            :param payment_method_code: The payment method used for the payment

            :return: True if the payment method is set to **iso20022_se** and the bank account
                     is not IBAN, else False.
        """
        return (
            payment_method_code == 'iso20022_se'
            and self.bank_account_id.acc_type in {'bban_se', 'plusgiro', 'bankgiro'}
        ) or self.env.context.get('bban')

    def _get_CtgyPurp(self, payment_method_code):
        if not self._is_se_bban(payment_method_code):
            return super()._get_CtgyPurp(payment_method_code)

        CtgyPurp = etree.Element('CtgyPurp')
        Cd = etree.SubElement(CtgyPurp, 'Cd')
        Cd.text = 'SALA' if self.env.context.get('sepa_payroll_sala') else 'SUPP'
        return CtgyPurp

    # TODO: remove partner_acc_type arg in master
    def _get_DbtrAcctOthr(self, payment_method_code=None, partner_acc_type=None):
        # EXTEND of account_iso20022
        Othr = super()._get_DbtrAcctOthr(payment_method_code)
        if self._is_se_bban(payment_method_code):
            SchmeNm = etree.SubElement(Othr, "SchmeNm")
            if self.bank_account_id.acc_type == 'bankgiro':
                Prtry = etree.SubElement(SchmeNm, "Prtry")
                Prtry.text = 'BGNR'
            else:
                Cd = etree.SubElement(SchmeNm, "Cd")
                Cd.text = 'BBAN'
        return Othr

    def _get_CdtrAcctIdOthr(self, bank_account, payment_method_code=None):
        if not self._is_se_bban(payment_method_code):
            return super()._get_CdtrAcctIdOthr(bank_account, payment_method_code)

        Othr = etree.Element("Othr")
        Id = etree.SubElement(Othr, "Id")
        Id.text = bank_account.sanitized_acc_number
        SchmeNm = etree.SubElement(Othr, "SchmeNm")
        if bank_account.acc_type == 'bankgiro':
            Prtry = etree.SubElement(SchmeNm, "Prtry")
            Prtry.text = 'BGNR'
        else:
            Cd = etree.SubElement(SchmeNm, "Cd")
            Cd.text = 'BBAN'
        return Othr

    def _get_FinInstnId(self, bank_account, payment_method_code, mode=None):
        if not self._is_se_bban(payment_method_code):
            return super()._get_FinInstnId(bank_account, payment_method_code, mode=mode)

        FinInstnId = etree.Element("FinInstnId")
        bic_code = self._get_cleaned_bic_code(bank_account, payment_method_code)
        if mode == 'DbtrAgt':
            BIC = etree.SubElement(FinInstnId, self._get_bic_tag(payment_method_code))
            BIC.text = bic_code
            return FinInstnId

        ClrSysMmbId = etree.SubElement(FinInstnId, "ClrSysMmbId")
        ClrSysId = etree.SubElement(ClrSysMmbId, "ClrSysId")
        Cd = etree.SubElement(ClrSysId, "Cd")
        Cd.text = "SESBA"
        MmbId = etree.SubElement(ClrSysMmbId, "MmbId")
        if bank_account.acc_type == 'bankgiro':
            MmbId.text = '9900'
        elif bank_account.acc_type == 'plusgiro':
            bank_code, _acc_num, _checksum = bank_account._se_get_acc_number_data(bank_account.acc_number)
            MmbId.text = '9960' if bank_code and bank_code.startswith('996') else '9500'
        else:
            if not bank_account.acc_number.isdigit():
                _bban, bank_code = bank_account._se_get_bban_from_iban()
            else:
                bank_code, _acc_num, _checksum = bank_account._se_get_acc_number_data(bank_account.acc_number)
            MmbId.text = bank_code
        return FinInstnId

    def _get_RmtInf(self, payment_method_code, payment):
        RmtInf = super()._get_RmtInf(payment_method_code, payment)
        if RmtInf is False or not self._is_se_bban(payment_method_code):
            return RmtInf

        strd = RmtInf.find('Strd')
        if strd is not None:
            partner_bank_id = payment.get('partner_bank_id')
            if partner_bank_id:
                partner_bank = self.env['res.partner.bank'].browse(partner_bank_id)
                if partner_bank and partner_bank.acc_type == 'bankgiro':
                    # if we got structured reference and the recipient has an account of type bankgiro, we need RfdDocAmt.
                    currency_id = payment.get('currency_id')
                    if currency_id:
                        ccy = self.env['res.currency'].browse(currency_id)
                        RfrdDocAmt = etree.Element('RfrdDocAmt')
                        if payment['payment_type'] == 'inbound':
                            CdtNoteAmt = etree.SubElement(RfrdDocAmt, 'CdtNoteAmt', Ccy=ccy.name)
                            CdtNoteAmt.text = float_repr(ccy.round(payment['amount']), 2)
                            RmtdAmt = etree.SubElement(RfrdDocAmt, 'RmtdAmt', Ccy=ccy.name)
                            RmtdAmt.text = '0.00'
                        elif payment['payment_type'] == 'outbound':
                            CdtNoteAmt = etree.SubElement(RfrdDocAmt, 'CdtNoteAmt', Ccy=ccy.name)
                            CdtNoteAmt.text = '0.00'
                            RmtdAmt = etree.SubElement(RfrdDocAmt, 'RmtdAmt', Ccy=ccy.name)
                            RmtdAmt.text = float_repr(ccy.round(payment['amount']), 2)
                        strd.insert(0, RfrdDocAmt)
        return RmtInf

    def _skip_CdtrAgt(self, partner_bank, payment_method_code):
        """
        Determine whether to skip the Creditor Agent (CdtrAgt) element in SEPA XML.

        This override ensures that for Swedish Bankgiro and Plusgiro accounts,
        the CdtrAgt element is always included, even if the BIC is missing.

        For other accounts or payment methods, the standard behavior is preserved.

        :param partner_bank: The partner's bank account record.
        :type partner_bank: res.partner.bank
        :param payment_method_code: The payment method code, e.g., 'iso20022_se'.
        :type payment_method_code: str
        :return: False to indicate that CdtrAgt should not be skipped, or the
                 result of the standard implementation.
        :rtype: bool
        """
        if payment_method_code == 'iso20022_se' and partner_bank.acc_type in ('bankgiro', 'plusgiro'):
            return False
        return super()._skip_CdtrAgt(partner_bank, payment_method_code)
