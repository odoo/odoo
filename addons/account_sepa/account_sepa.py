# -*- coding: utf-8 -*-

import re
import time
import random

from unidecode import unidecode

from openerp import models, fields, api, _
from openerp.tools import float_round
from openerp.exceptions import UserError, ValidationError

# TransientModel ? Doit pouvoir ^etre étendu, garder un état interne et potentiellement
# proposer un wizard

# pour l'extensibilité, diviser _create_pain_001_001_03_document en une myriade de petites méthodes ?

# message "generic": _require_generic() ? Puis des if un peu partout ?

class account_sepa(models.Model):
    _name = "account.sepa"
    _description = "SEPA files generation facilities"

    def _group_payments_by_journal(self, payment_recs):
        """ Return a list of account.payment recordsets, one for each journal """
        journal_ids = list(set(map(lambda r: r.journal_id.id, payment_recs)))
        return map(lambda journal_id: payment_recs.filtered(lambda r: r.journal_id.id == journal_id), journal_ids)

    def _prepare_string(self, string):
        while '//' in string: # No double slash allowed
            string = string.replace('//','/')
        while string.startswith('/'): # No leading slash allowed
            string = string[1:]
        while string.endswith('/'): # No ending slash allowed
            string = string[:-1]
        string = unicode(a, 'UTF-8') # Make sure the string is in UTF-8
        string = unidecode(string) # Try to convert unicode characters to ASCII
        string = re.sub('[^A-Za-z0-9/-?:().,\'+ ]', '', string) # Only keep allowed characters
        return string
        # Without third-party module but not perfect (eg. will drop œ or €) :
        # return unicodedata.normalize('NFD', unicode(string, 'UTF-8')).encode('ascii', 'ignore')

    @api.v7
    def create_sepa_ct(self, cr, uid, payment_ids, context=None):
        payment_recs = self.pool['account.payment'].browse(cr, uid, payment_ids, context=context)
        self.pool['account.sepa'].browse(cr, uid, [], context=context).create_sepa_ct(payment_recs)

    @api.v8
    def create_sepa_ct(self, payment_recs):
        # One file per recipient financial institution
        for recordset in self._group_payments_by_journal(payment_recs):
            print self._create_pain_001_001_03_document(recordset)

    def _create_pain_001_001_03_document(self, file_payments):
        """ :param file_payments: account.payment recordset representing payments to be exported """
        if len(file_payments) < 0:
            raise osv.except_osv(_('Programming Error'), _("No payment selected."))
        doc = []

        MsgId = str(int(time.time()*100))[-10:]
        MsgId = self.env.user.company_id.name[-15:] + MsgId
        MsgId = str(random.random()) + MsgId
        MsgId = MsgId[-30:]
        CreDtTm = time.strftime("%Y-%m-%dT%H:%M:%S")
        NbOfTxs = str(len(file_payments))
        if len(NbOfTxs) > 15:
            raise ValidationError(_("Too many transactions for a single file."))
        CtrlSum = self._get_CtrlSum(file_payments)
        Nm = self.env.user.company_id.sepa_initiating_party_name

        doc.append("<?xml version='1.0' encoding='UTF-8'?>")
        doc.append("<Document xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns='urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'>")
        doc.append("\t<CstmrCdtTrfInitn>")
        doc.append("\t\t<GrpHdr>")
        doc.append("\t\t\t<MsgId>" + MsgId + "</MsgId>")
        doc.append("\t\t\t<CreDtTm>" + CreDtTm + "</CreDtTm>")
        doc.append("\t\t\t<NbOfTxs>" + NbOfTxs + "</NbOfTxs>")
        doc.append("\t\t\t<CtrlSum>" + CtrlSum + "</CtrlSum>")
        doc.append("\t\t\t<InitgPty>")
        doc.append("\t\t\t\t<Nm>" + Nm + "</Nm>")
        doc.append("\t\t\t</InitgPty>")
        doc.append("\t\t</GrpHdr>")

        # One PmtInf per bank account
        for acc_payments in self._group_payments_by_journal(file_payments):
            PmtInfId = (MsgId + str(acc_payments[0].journal_id.id))[-30:] # or account IBAN
            NbOfTxs = str(len(acc_payments))
            CtrlSum = self._get_CtrlSum(acc_payments)
            IBAN = "TODO" # TODO
            BIC = "TODO" # TODO

            doc.append("\t\t<PmtInf>")
            doc.append("\t\t\t<PmtInfId>" + PmtInfId + "</PmtInfId>")
            doc.append("\t\t\t<PmtMtd>TRF</PmtMtd>") # CHK could be used to issue a check, but that isn't pain.001.001.03 compliant
            doc.append("\t\t\t<BtchBookg>false</BtchBookg>") # TODO
            doc.append("\t\t\t<NbOfTxs>" + NbOfTxs + "</NbOfTxs>")
            doc.append("\t\t\t<CtrlSum>" + CtrlSum + "</CtrlSum>")
            doc.append("\t\t\t<Dbtr>")
            doc.append("\t\t\t\t<Nm>" + Nm + "</Nm>")
            doc.append("\t\t\t</Dbtr>")
            doc.append("\t\t\t<DbtrAcct>")
            doc.append("\t\t\t\t<Id>")
            doc.append("\t\t\t\t\t<IBAN>" + IBAN + "<IBAN>")
            doc.append("\t\t\t\t</Id>")
            doc.append("\t\t\t</DbtrAcct>")
            doc.append("\t\t\t<DbtrAgt>")
            doc.append("\t\t\t\t<FinInstnId>")
            doc.append("\t\t\t\t\t<BIC>" + BIC + "</BIC>")
            doc.append("\t\t\t\t</FinInstnId>")
            doc.append("\t\t\t</DbtrAgt>")

            # One CdtTrfTxInf per transaction
            for payments in acc_payments:
                InstrId = "TODO" # Used in the debtor bank for reporting and bank statements
                EndToEndId = (PmtInfId + str(payments.id))[-30:]
                InstdAmt = str(float_round(aml.payment_amount, 2))
                if len(payments.partner_id.bank_ids) <= 0:
                    raise UserError(_("There is no bank account recorded for %s") % payments.partner_id.name)
                partner_bank = payments.partner_id.bank_ids[0] # TODO
                BIC = partner_bank.bank_bic
                Nm = payments.partner_id.name[:70]
                IBAN = partner_bank.state="iban" and partner_bank.acc_number or 'TODO'

                doc.append("\t\t\t<CdtTrfTxInf>")
                doc.append("\t\t\t\t<PmtId>")
                doc.append("\t\t\t\t\t<InstrId>" + InstrId + "</InstrId>")
                doc.append("\t\t\t\t\t<EndToEndId>" + EndToEndId + "</EndToEndId>")
                doc.append("\t\t\t\t</PmtId>")
                doc.append("\t\t\t\t<Amt>")
                doc.append("\t\t\t\t\t<InstdAmt>" + InstdAmt + "</InstdAmt>")
                doc.append("\t\t\t\t</Amt>")
                if BIC:
                    doc.append("\t\t\t\t<CdtrAgt>")
                    doc.append("\t\t\t\t\t<FinInstnId>")
                    doc.append("\t\t\t\t\t\t<BIC>" + BIC + "</BIC>")
                    doc.append("\t\t\t\t\t</FinInstnId>")
                    doc.append("\t\t\t\t</CdtrAgt>")
                doc.append("\t\t\t\t<Cdtr>")
                doc.append("\t\t\t\t\t<Nm>" + Nm + "</Nm>")
                doc.append("\t\t\t\t</Cdtr>")
                doc.append("\t\t\t\t<CdtrAcct>")
                doc.append("\t\t\t\t\t<Id>")
                doc.append("\t\t\t\t\t\t<IBAN>" + IBAN + "<IBAN>")
                doc.append("\t\t\t\t\t</Id>")
                doc.append("\t\t\t\t</CdtrAcct>")
                doc.append("\t\t\t</CdtTrfTxInf>")

            doc.append("\t\t</PmtInf>")
        doc.append("\t</CstmrCdtTrfInitn>")
        doc.append("</Document>")
        return ''.join(doc)

    def _get_CtrlSum(self, payment_recs):
        return str(float_round(sum(payment.payment_amount for payment in payment_recs), 2))

    # _get_InitgPty(self):
    #   """ For credit transfers sent via odoo, the initiating party, debtor and ultimate debtor are the same """
