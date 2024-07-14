# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import time
from collections import defaultdict
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr, float_round

import odoo.addons.account.tools.structured_reference as sr
from odoo.addons.account_batch_payment.models.sepa_mapping import _replace_characters_SEPA


def sanitize_communication(communication, size=140):
    """ Returns a sanitized version of the communication given in parameter,
        so that:
            - it contains only latin characters
            - it does not contain any //
            - it does not start or end with /
            - it is maximum 140 characters long
        (these are the SEPA compliance criteria)
    """
    while '//' in communication:
        communication = communication.replace('//', '/')
    if communication.startswith('/'):
        communication = communication[1:]
    if communication.endswith('/'):
        communication = communication[:-1]
    communication = _replace_characters_SEPA(communication, size)
    return communication

class AccountJournal(models.Model):
    _inherit = "account.journal"

    sepa_pain_version = fields.Selection(
        [
            ('pain.001.001.03', 'Generic'),
            ('pain.001.001.03.austrian.004', 'Austrian'),
            ('pain.001.001.03.de', 'German'),
            ('pain.001.001.03.se', 'Swedish'),
            ('pain.001.001.03.ch.02', 'Swiss'),
            ('pain.001.001.09', 'New generic version (09)'),
            ('iso_20022', 'ISO 20022'),
        ],
        string='SEPA Pain Version',
        readonly=False,
        store=True,
        compute='_compute_sepa_pain_version',
        help='SEPA may be a generic format, some countries differ from the '
             'SEPA recommendations made by the EPC (European Payment Council) '
             'and thus the XML created need some tweaking.'
    )
    has_sepa_ct_payment_method = fields.Boolean(compute='_compute_has_sepa_ct_payment_method')

    @api.depends('bank_acc_number', 'country_code', 'company_id.country_code')
    def _compute_sepa_pain_version(self):
        """ Set default value for the field sepa_pain_version"""

        pains_by_country = {
            'DE': 'pain.001.001.03.de',
            'CH': 'pain.001.001.03.ch.02',
            'SE': 'pain.001.001.03.se',
            'AT': 'pain.001.001.03.austrian.004',
        }

        for rec in self:
            # First try to retrieve the country_code from the IBAN
            if rec.bank_acc_number and re.match('^[A-Z]{2}[0-9]{2}.*', rec.bank_acc_number):
                country_code = rec.bank_acc_number[:2]
            # Then try from the company's fiscal country, and finally from the company's country
            else:
                country_code = rec.country_code or rec.company_id.country_code or ""

            rec.sepa_pain_version = pains_by_country.get(country_code, 'pain.001.001.03')

    @api.depends('outbound_payment_method_line_ids.payment_method_id.code')
    def _compute_has_sepa_ct_payment_method(self):
        for rec in self:
            rec.has_sepa_ct_payment_method = any(
                payment_method.payment_method_id.code == 'sepa_ct'
                for payment_method in rec.outbound_payment_method_line_ids
            )

    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available('sepa_ct'):
            res |= self.env.ref('account_sepa.account_payment_method_sepa_ct')
        return res

    def create_iso20022_credit_transfer(self, payments, batch_booking=False, sct_generic=False):
        """
            This method creates the body of the XML file for the SEPA document.
            It returns the content of the XML file.
        """
        pain_version = self.sepa_pain_version
        Document = self._get_document(pain_version)
        CstmrCdtTrfInitn = etree.SubElement(Document, "CstmrCdtTrfInitn")

        # Create the GrpHdr XML block
        GrpHdr = etree.SubElement(CstmrCdtTrfInitn, "GrpHdr")
        MsgId = etree.SubElement(GrpHdr, "MsgId")
        val_MsgId = str(time.time())
        MsgId.text = val_MsgId
        CreDtTm = etree.SubElement(GrpHdr, "CreDtTm")
        CreDtTm.text = time.strftime("%Y-%m-%dT%H:%M:%S")
        NbOfTxs = etree.SubElement(GrpHdr, "NbOfTxs")
        val_NbOfTxs = str(len(payments))
        if len(val_NbOfTxs) > 15:
            raise ValidationError(_("Too many transactions for a single file."))
        NbOfTxs.text = val_NbOfTxs
        CtrlSum = etree.SubElement(GrpHdr, "CtrlSum")
        CtrlSum.text = self._get_CtrlSum(payments)
        GrpHdr.append(self._get_InitgPty(pain_version, sct_generic))

        # Create one PmtInf XML block per execution date, per currency
        payments_date_instr_wise = defaultdict(lambda: [])
        today = fields.Date.today()
        for payment in payments:
            required_payment_date = payment['payment_date'] if payment['payment_date'] > today else today
            currency = payment['currency_id'] or self.company_id.currency_id.id
            payments_date_instr_wise[(required_payment_date, currency)].append(payment)
        count = 0
        for (payment_date, currency), payments_list in payments_date_instr_wise.items():
            count += 1
            PmtInf = etree.SubElement(CstmrCdtTrfInitn, "PmtInf")
            PmtInfId = etree.SubElement(PmtInf, "PmtInfId")
            PmtInfId.text = (val_MsgId + str(self.id) + str(count))[-30:]
            PmtMtd = etree.SubElement(PmtInf, "PmtMtd")
            PmtMtd.text = 'TRF'
            BtchBookg = etree.SubElement(PmtInf, "BtchBookg")
            BtchBookg.text = batch_booking and 'true' or 'false'
            NbOfTxs = etree.SubElement(PmtInf, "NbOfTxs")
            NbOfTxs.text = str(len(payments_list))
            CtrlSum = etree.SubElement(PmtInf, "CtrlSum")
            CtrlSum.text = self._get_CtrlSum(payments_list)

            PmtTpInf = self._get_PmtTpInf(sct_generic)
            if len(PmtTpInf) != 0: #Boolean conversion from etree element triggers a deprecation warning ; this is the proper way
                PmtInf.append(PmtTpInf)

            ReqdExctnDt = etree.SubElement(PmtInf, "ReqdExctnDt")
            if pain_version == "pain.001.001.09":
                Dt = etree.SubElement(ReqdExctnDt, "Dt")
                Dt.text = fields.Date.to_string(payment_date)
            else:
                ReqdExctnDt.text = fields.Date.to_string(payment_date)
            PmtInf.append(self._get_Dbtr(pain_version, sct_generic))
            PmtInf.append(self._get_DbtrAcct())
            DbtrAgt = etree.SubElement(PmtInf, "DbtrAgt")
            FinInstnId = etree.SubElement(DbtrAgt, "FinInstnId")
            bank_account = self.bank_account_id
            bic_code = self._get_cleaned_bic_code(bank_account)
            if pain_version in ['pain.001.001.03.se', 'pain.001.001.03.ch.02'] and not bic_code:
                raise UserError(_("Bank account %s 's bank does not have any BIC number associated. Please define one.", bank_account.sanitized_acc_number))
            bic_tag = pain_version == "pain.001.001.09" and "BICFI" or "BIC"
            if bic_code:
                BIC = etree.SubElement(FinInstnId, bic_tag)
                BIC.text = bic_code
            else:
                Othr = etree.SubElement(FinInstnId, "Othr")
                Id = etree.SubElement(Othr, "Id")
                Id.text = "NOTPROVIDED"
            PmtInf.append(self._get_ChrgBr(sct_generic))

            # One CdtTrfTxInf per transaction
            for payment in payments_list:
                PmtInf.append(self._get_CdtTrfTxInf(PmtInfId, payment, sct_generic, pain_version))

        return etree.tostring(Document, pretty_print=True, xml_declaration=True, encoding='utf-8')

    def _get_document(self, pain_version):
        if pain_version == 'pain.001.001.03.ch.02':
            Document = self._create_pain_001_001_03_ch_document()
        elif pain_version == 'pain.001.001.09':
            Document = self._create_iso20022_document('pain.001.001.09')
        else: #The German version will also use the create_pain_001_001_03_document since the version 001.003.03 is deprecated
            Document = self._create_pain_001_001_03_document()

        return Document

    def _create_pain_001_001_03_document(self):
        """ Create a sepa credit transfer file that follows the European Payment Councile generic guidelines (pain.001.001.03)

            :param doc_payments: recordset of account.payment to be exported in the XML document returned
        """
        Document = self._create_iso20022_document('pain.001.001.03')
        return Document

    def _create_pain_001_001_03_ch_document(self):
        """ Create a sepa credit transfer file that follows the swiss specific guidelines, as established
            by SIX Interbank Clearing (pain.001.001.03.ch.02)

            :param doc_payments: recordset of account.payment to be exported in the XML document returned
        """
        Document = etree.Element("Document", nsmap={
            None: "http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd",
            'xsi': "http://www.w3.org/2001/XMLSchema-instance"})
        return Document

    def _create_iso20022_document(self, pain_version):
        return etree.Element("Document", nsmap={
            None: "urn:iso:std:iso:20022:tech:xsd:%s" % (pain_version,),
            'xsi': "http://www.w3.org/2001/XMLSchema-instance"})

    def _get_CtrlSum(self, payments):
        return float_repr(float_round(sum(payment['amount'] for payment in payments), 2), 2)

    def _get_InitgPty(self, pain_version, sct_generic=False):
        InitgPty = etree.Element("InitgPty")
        if pain_version == 'pain.001.001.03.se':
            InitgPty.extend(self._get_company_PartyIdentification32(sct_generic, org_id=True, postal_address=False, issr=False, nm=False, schme_nm='BANK'))
        elif pain_version == 'pain.001.001.03.austrian.004':
            InitgPty.extend(self._get_company_PartyIdentification32(sct_generic, org_id=True, postal_address=False, issr=False))
        else:
            InitgPty.extend(self._get_company_PartyIdentification32(sct_generic, org_id=True, postal_address=False, issr=True))
        return InitgPty

    def _get_company_PartyIdentification32(self, sct_generic=False, org_id=True, postal_address=True, nm=True, issr=True, schme_nm=False):
        """ Returns a PartyIdentification32 element identifying the current journal's company
        """
        ret = []
        company = self.company_id
        name_length = sct_generic and 35 or 70

        if nm:
            Nm = etree.Element("Nm")
            if company.sepa_initiating_party_name:
                company_name = company.sepa_initiating_party_name[:name_length]
            else:
                company_name = company.name[:name_length]
            Nm.text = sanitize_communication(company_name)
            ret.append(Nm)

        if postal_address:
            PstlAdr = self._get_PstlAdr(company.partner_id)
            if PstlAdr is not None:
                ret.append(PstlAdr)

        if org_id and company.sepa_orgid_id:
            Id = etree.Element("Id")
            OrgId = etree.SubElement(Id, "OrgId")
            if self.sepa_pain_version == "pain.001.001.09" and self.company_id.account_sepa_lei:
                LEI = etree.SubElement(OrgId, "LEI")
                LEI.text = self.company_id.account_sepa_lei
            Othr = etree.SubElement(OrgId, "Othr")
            _Id = etree.SubElement(Othr, "Id")
            _Id.text = sanitize_communication(company.sepa_orgid_id)
            if issr and company.sepa_orgid_issr:
                Issr = etree.SubElement(Othr, "Issr")
                Issr.text = sanitize_communication(company.sepa_orgid_issr)
            if schme_nm:
                SchmeNm = etree.SubElement(Othr, "SchmeNm")
                Cd = etree.SubElement(SchmeNm, "Cd")
                Cd.text = schme_nm
            ret.append(Id)

        return ret

    def _get_PmtTpInf(self, sct_generic=False):
        PmtTpInf = etree.Element("PmtTpInf")

        is_salary = self.env.context.get('sepa_payroll_sala')

        if is_salary:
            # The "High" priority level is also an attribute of the payment
            # that we should specify as well for salary payments
            # See https://www.febelfin.be/sites/default/files/2019-04/standard-credit_transfer-xml-v32-en_0.pdf section 2.6
            InstrPrty = etree.SubElement(PmtTpInf, "InstrPrty")
            InstrPrty.text = 'HIGH'

        if self.sepa_pain_version != 'pain.001.001.03.ch.02':
            SvcLvl = etree.SubElement(PmtTpInf, "SvcLvl")
            Cd = etree.SubElement(SvcLvl, "Cd")
            Cd.text = 'NURG' if sct_generic else 'SEPA'

        if is_salary:
            # The SALA purpose code is standard for all SEPA, and guarantees a series
            # of things in instant payment: https://www.sepaforcorporates.com/sepa-payments/sala-sepa-salary-payments.
            CtgyPurp = etree.SubElement(PmtTpInf, "CtgyPurp")
            Cd = etree.SubElement(CtgyPurp, "Cd")
            Cd.text = 'SALA'

        return PmtTpInf

    def _get_Dbtr(self, pain_version, sct_generic=False):
        Dbtr = etree.Element("Dbtr")
        if pain_version == "pain.001.001.03.se":
            Dbtr.extend(self._get_company_PartyIdentification32(sct_generic, org_id=True, postal_address=True, issr=False, schme_nm="CUST"))
        else:
            Dbtr.extend(self._get_company_PartyIdentification32(sct_generic, org_id=not sct_generic, postal_address=True))
        return Dbtr

    def _get_DbtrAcct(self):
        DbtrAcct = etree.Element("DbtrAcct")
        Id = etree.SubElement(DbtrAcct, "Id")
        IBAN = etree.SubElement(Id, "IBAN")
        IBAN.text = self.bank_account_id.sanitized_acc_number
        Ccy = etree.SubElement(DbtrAcct, "Ccy")
        Ccy.text = self.currency_id and self.currency_id.name or self.company_id.currency_id.name

        return DbtrAcct

    def _get_PstlAdr(self, partner_id):
        pstl_addr_list = partner_id._get_all_addr()
        pstl_addr_list = [addr for addr in pstl_addr_list if addr['country']]
        if not partner_id.is_company:
            if not pstl_addr_list:
                return None
            pstl_addr_list = [
                addr for addr in pstl_addr_list if (
                    addr['city'] or
                    # SE only needs country
                    self.sepa_pain_version == 'pain.001.001.03.se'
                )
            ]
            if not pstl_addr_list:
                return None

            pstl_addr = None
            if len(pstl_addr_list) > 1:
                for addr_dict in pstl_addr_list:
                    if addr_dict['contact_type'] == 'employee':
                        pstl_addr = addr_dict
            pstl_addr = pstl_addr or pstl_addr_list[0]
        else:
            if not pstl_addr_list:
                raise ValidationError(_('Partner %s has no country code defined.', partner_id.name))
            pstl_addr = pstl_addr_list[0]

        PstlAdr = etree.Element("PstlAdr")
        if self.sepa_pain_version == 'pain.001.001.09':
            for node_name, attr, size in [('StrtNm', 'street', 70), ('PstCd', 'zip', 140), ('TwnNm', 'city', 140)]:
                if pstl_addr[attr]:
                    address_element = etree.SubElement(PstlAdr, node_name)
                    address_element.text = sanitize_communication(pstl_addr[attr], size)

        Ctry = etree.SubElement(PstlAdr, 'Ctry')
        Ctry.text = pstl_addr['country']

        if self.sepa_pain_version != 'pain.001.001.09':
            # Some banks seem allergic to having the zip in a separate tag, so we do as before
            if pstl_addr['street']:
                AdrLine = etree.SubElement(PstlAdr, 'AdrLine')
                AdrLine.text = sanitize_communication(pstl_addr['street'], 70)
            if pstl_addr['zip'] and pstl_addr['city']:
                AdrLine = etree.SubElement(PstlAdr, 'AdrLine')
                AdrLine.text = sanitize_communication(pstl_addr['zip'] + ' ' + pstl_addr['city'], 70)

        return PstlAdr

    def _skip_CdtrAgt(self, partner_bank, pain_version):
        return (
            not partner_bank.bank_id.bic
            or (
                # Creditor Agent can be omitted with IBAN and QR-IBAN accounts
                pain_version == 'pain.001.001.03.ch.02'
                and self._is_qr_iban({'partner_bank_id' : partner_bank.id, 'journal_id' : self.id})
            )
        )

    def _get_CdtTrfTxInf(self, PmtInfId, payment, sct_generic, pain_version):
        CdtTrfTxInf = etree.Element("CdtTrfTxInf")
        PmtId = etree.SubElement(CdtTrfTxInf, "PmtId")
        if payment['name']:
            InstrId = etree.SubElement(PmtId, "InstrId")
            InstrId.text = sanitize_communication(payment['name'], 35)
        EndToEndId = etree.SubElement(PmtId, "EndToEndId")
        EndToEndId.text = (PmtInfId.text + str(payment['id']))[-30:].strip()
        Amt = etree.SubElement(CdtTrfTxInf, "Amt")

        currency_id = self.env['res.currency'].search([('id', '=', payment['currency_id'])], limit=1)
        journal_id = self.env['account.journal'].search([('id', '=', payment['journal_id'])], limit=1)
        val_Ccy = currency_id and currency_id.name or journal_id.company_id.currency_id.name
        val_InstdAmt = float_repr(float_round(payment['amount'], 2), 2)
        max_digits = val_Ccy == 'EUR' and 11 or 15
        if len(re.sub(r'\.', '', val_InstdAmt)) > max_digits:
            raise ValidationError(_(
                "The amount of the payment '%(payment)s' is too high. The maximum permitted is %(limit)s.",
                payment=payment['name'],
                limit=str(9) * (max_digits - 2) + ".99",
            ))
        InstdAmt = etree.SubElement(Amt, "InstdAmt", Ccy=val_Ccy)
        InstdAmt.text = val_InstdAmt

        partner = self.env['res.partner'].sudo().browse(payment['partner_id'])

        partner_bank_id = payment.get('partner_bank_id')
        if not partner_bank_id:
            raise UserError(_('Partner %s has not bank account defined.', partner.name))

        partner_bank = self.env['res.partner.bank'].sudo().browse(partner_bank_id)

        if not self._skip_CdtrAgt(partner_bank, pain_version):
            CdtTrfTxInf.append(self._get_CdtrAgt(partner_bank, sct_generic, pain_version))

        Cdtr = etree.SubElement(CdtTrfTxInf, "Cdtr")
        Nm = etree.SubElement(Cdtr, "Nm")
        Nm.text = sanitize_communication((
            partner_bank.acc_holder_name or partner.name or partner.commercial_partner_id.name or '/'
        )[:70]).strip() or '/'
        PstlAdr = self._get_PstlAdr(partner)
        if PstlAdr is not None:
            Cdtr.append(PstlAdr)

        CdtTrfTxInf.append(self._get_CdtrAcct(partner_bank, sct_generic))

        val_RmtInf = self._get_RmtInf(payment)
        if val_RmtInf is not False:
            CdtTrfTxInf.append(val_RmtInf)

        if self.sepa_pain_version == "pain.001.001.09":
            UETR = etree.SubElement(PmtId, "UETR")
            UETR.text = payment["sepa_uetr"]

        return CdtTrfTxInf

    def _get_ChrgBr(self, sct_generic):
        ChrgBr = etree.Element("ChrgBr")
        ChrgBr.text = sct_generic and "SHAR" or "SLEV"
        return ChrgBr

    def _get_CdtrAgt(self, bank_account, sct_generic, pain_version):
        CdtrAgt = etree.Element("CdtrAgt")
        FinInstnId = etree.SubElement(CdtrAgt, "FinInstnId")
        bic_code = self._get_cleaned_bic_code(bank_account)
        if bic_code:
            BIC = etree.SubElement(FinInstnId, "BIC")
            BIC.text = bic_code
            if self.sepa_pain_version == "pain.001.001.09":
                BIC.tag = "BICFI"
            partner_lei = bank_account.partner_id.account_sepa_lei
        if self.sepa_pain_version == "pain.001.001.09" and partner_lei:
            # LEI needs to be inserted after BIC
            LEI = etree.SubElement(FinInstnId, "LEI")
            LEI.text = partner_lei
        if not bic_code:
            if pain_version in ['pain.001.001.03.austrian.004', 'pain.001.001.03.ch.02']:
                # Othr and NOTPROVIDED are not supported in CdtrAgt by those flavours
                raise UserError(_("The bank defined on account %s (from partner %s) has no BIC. Please first set one.", bank_account.acc_number, bank_account.partner_id.name))

            Othr = etree.SubElement(FinInstnId, "Othr")
            Id = etree.SubElement(Othr, "Id")
            Id.text = "NOTPROVIDED"

        return CdtrAgt

    def _get_CdtrAcct(self, bank_account, sct_generic):
        if not sct_generic and (not bank_account.acc_type or not bank_account.acc_type == 'iban'):
            raise UserError(_("The account %s, linked to partner '%s', is not of type IBAN.\nA valid IBAN account is required to use SEPA features.", bank_account.acc_number, bank_account.partner_id.name))

        CdtrAcct = etree.Element("CdtrAcct")
        Id = etree.SubElement(CdtrAcct, "Id")
        if sct_generic and bank_account.acc_type != 'iban':
            Othr = etree.SubElement(Id, "Othr")
            _Id = etree.SubElement(Othr, "Id")
            acc_number = bank_account.acc_number
            # CH case when when we have non-unique account numbers
            if " " in bank_account.sanitized_acc_number and " " in bank_account.acc_number:
                acc_number = bank_account.acc_number.split(" ")[0]
            _Id.text = acc_number
        else:
            IBAN = etree.SubElement(Id, "IBAN")
            IBAN.text = bank_account.sanitized_acc_number

        return CdtrAcct

    def _get_RmtInf(self, payment):
        def detect_reference_type(reference, partner_country_code):
            if partner_country_code == 'BE' and sr.is_valid_structured_reference_be(reference):
                return 'be'
            elif self._is_qr_iban(payment):
                return 'ch'
            elif partner_country_code == 'FI' and sr.is_valid_structured_reference_fi(reference):
                return 'fi'
            elif partner_country_code == 'NO' and sr.is_valid_structured_reference_no_se(reference):
                return 'no'
            elif partner_country_code == 'SE' and sr.is_valid_structured_reference_no_se(reference):
                return 'se'
            elif sr.is_valid_structured_reference_iso(reference):
                return 'iso'
            else:
                return None

        def get_strd_tree(ref, cd=None, prtry=None, issr=None):
            strd_string = f"""
                <Strd>
                    <CdtrRefInf>
                        <Tp>
                            <CdOrPrtry>
                                <Cd>{cd}</Cd>
                                <Prtry>{prtry}</Prtry>
                            </CdOrPrtry>
                            <Issr>{issr}</Issr>
                        </Tp>
                        <Ref>{ref}</Ref>
                    </CdtrRefInf>
                </Strd>
            """
            strd_tree = etree.fromstring(strd_string)
            if not cd:
                cd_tree = strd_tree.find('.//Cd')
                cd_tree.getparent().remove(cd_tree)
            if not prtry:
                prtry_tree = strd_tree.find('.//Prtry')
                prtry_tree.getparent().remove(prtry_tree)
            if not issr:
                issr_tree = strd_tree.find('.//Issr')
                issr_tree.getparent().remove(issr_tree)
            return strd_tree


        if not payment['ref']:
            return False
        RmtInf = etree.Element('RmtInf')
        ref = sr.sanitize_structured_reference(payment['ref'])
        partner_country_code = payment.get('partner_country_code')
        reference_type = detect_reference_type(ref, partner_country_code)

        # Check whether we have a structured communication
        if reference_type == 'iso':
            RmtInf.append(get_strd_tree(ref, cd='SCOR', issr='ISO'))
        elif reference_type == 'be':
            RmtInf.append(get_strd_tree(ref, cd='SCOR', issr='BBA'))
        elif reference_type == 'ch':
            ref = ref.rjust(27, '0')
            RmtInf.append(get_strd_tree(ref, prtry='QRR'))
        elif reference_type in ('fi', 'no', 'se'):
            RmtInf.append(get_strd_tree(ref, cd='SCOR'))
        else:
            Ustrd = etree.SubElement(RmtInf, "Ustrd")
            Ustrd.text = sanitize_communication(payment['ref'])
            # sanitize_communication() automatically removes leading slash
            # characters in payment references, due to the requirements of
            # European Payment Council, available here:
            # https://www.europeanpaymentscouncil.eu/document-library/implementation-guidelines/sepa-credit-transfer-customer-psp-implementation
            # (cfr Section 1.4 Character Set)

            # However, the /A/  four-character prefix is a requirement of belgian law.
            # The existence of such legal prefixes may be a reason why the leading slash
            # is forbidden in normal SEPA payment references, to avoid conflicts.

            # Legal references for Belgian salaries:
            # https://www.ejustice.just.fgov.be/eli/loi/1967/10/10/1967101056/justel#Art.1411bis
            # Article 1411bis of Belgian Judicial Code mandating the use of special codes
            # for identifying payments of protected amounts, and the related penalties
            # for payment originators, in case of misuse.

            # https://www.ejustice.just.fgov.be/eli/arrete/2006/07/04/2006009525/moniteur
            # Royal Decree defining "/A/ " as the code for salaries, in the context of
            # Article 1411bis
            if self.env.context.get('l10n_be_hr_payroll_sepa_salary_payment'):
                Ustrd.text = f"/A/ {Ustrd.text}"
        return RmtInf

    def _is_qr_iban(self, payment_dict):
        """ Tells if the bank account linked to the payment has a QR-IBAN account number.
        QR-IBANs are specific identifiers used in Switzerland as references in
        QR-codes. They are formed like regular IBANs, but are actually something
        different.
        """
        partner_bank = self.env['res.partner.bank'].browse(payment_dict['partner_bank_id'])
        company = self.env['account.journal'].browse(payment_dict['journal_id']).company_id
        iban = partner_bank.sanitized_acc_number
        if (
            partner_bank.acc_type != 'iban'
            or (partner_bank.sanitized_acc_number or '')[:2] not in ('CH', 'LI')
            or partner_bank.company_id.id not in (False, company.id)
            or len(iban) < 9
        ):
            return False
        iid_start_index = 4
        iid_end_index = 8
        iid = iban[iid_start_index : iid_end_index+1]
        return re.match(r'\d+', iid) \
            and 30000 <= int(iid) <= 31999 # Those values for iid are reserved for QR-IBANs only

    def _get_cleaned_bic_code(self, bank_account):
        """ Checks if the BIC code is matching the pattern from the XSD to avoid
            having files generated here that are refused by banks after.
            It also returns a cleaned version of the BIC as a convenient use.
        """
        if not bank_account.bank_bic:
            return
        regex = '[A-Z]{6,6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3,3}){0,1}'
        if self.sepa_pain_version == 'pain.001.001.09':
            regex = '[A-Z0-9]{4,4}[A-Z]{2,2}[A-Z0-9]{2,2}([A-Z0-9]{3,3}){0,1}'
        if not re.match(regex, bank_account.bank_bic):
            raise UserError(_("The BIC code '%s' associated to the bank '%s' of bank account '%s' "
                              "of partner '%s' does not respect the required convention.\n"
                              "It must contain 8 or 11 characters and match the following structure:\n"
                              "- 4 letters: institution code or bank code\n"
                              "- 2 letters: country code\n"
                              "- 2 letters or digits: location code\n"
                              "- 3 letters or digits: branch code, optional\n",
                              bank_account.bank_bic, bank_account.bank_id.name,
                              bank_account.sanitized_acc_number, bank_account.partner_id.name))
        return bank_account.bank_bic.replace(' ', '').upper()
