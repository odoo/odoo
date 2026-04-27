from lxml import etree
import base64
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestISO20022CommonCreditTransfer(AccountTestInvoicingCommon):
    @classmethod
    def collect_company_accounting_data(cls, company):
        company.update({
            'street': '4 Privet Drive',
            'city': 'Little Whinging',
            'zip': 1997,
            'iso20022_orgid_id': '0123456789',
            'iso20022_initiating_party_name': 'Grunnings'
        })

        return super().collect_company_accounting_data(company)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def create_payment(cls, bank_journal, partner, payment_method, amount, memo=None):
        """ Create a SEPA credit transfer payment """
        return cls.env['account.payment'].create({
            'journal_id': bank_journal.id,
            'payment_method_line_id': cls.payment_method_line.id,
            'payment_type': 'outbound',
            'date': '2024-03-04',
            'amount': amount,
            'partner_id': partner.id,
            'partner_type': 'supplier',
            'memo': memo,
        })

    def generate_iso20022_batch_payment(self, partner, memo=None):
        payment_1 = self.create_payment(self.company_data['default_journal_bank'], partner, self.payment_method, 500, memo)
        payment_1.action_post()
        payment_2 = self.create_payment(self.company_data['default_journal_bank'], partner, self.payment_method, 600, memo)
        payment_2.action_post()

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [(4, payment.id, None) for payment in (payment_1 | payment_2)],
            'payment_method_id': self.payment_method.id,
            'batch_type': 'outbound',
        })
        wizard_action = batch.validate_batch()
        self.assertIsNone(wizard_action)
        batch._send_after_validation()
        return batch

    def get_sct_doc_from_batch(self, batch):
        xml_doc = etree.fromstring(base64.b64decode(batch.export_file))
        # Check that all unique elements respect the ISO20022 constraints before replacing them for testing purpose
        namespace = {'ns': next(iter(xml_doc.nsmap.values()))}
        MsgId = xml_doc.find('.//ns:MsgId', namespaces=namespace)
        self.assertTrue(len(MsgId) <= 35)
        MsgId.text = '12345'
        Date = xml_doc.find('.//ns:CreDtTm', namespaces=namespace)
        # date format : 20yy-mm-ddThh:mm:ss
        date_regex = r'^20\d{2}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])T([0-1]?\d|2[0-3])(?::([0-5]?\d))?(?::([0-5]?\d))$'
        self.assertRegex(Date.text, date_regex)
        Date.text = '2024-03-04T08:21:16'
        PmtInfId = xml_doc.find('.//ns:PmtInfId', namespaces=namespace)
        self.assertTrue(len(PmtInfId) <= 35)
        PmtInfId.text = '1709540476.798265401'
        InstrId = xml_doc.findall('.//ns:InstrId', namespaces=namespace)
        for instr_id in InstrId:
            self.assertTrue(len(instr_id) <= 35)
            instr_id.text = '5-SCT-BNK1-2024-03-04'
        EndToEndId = xml_doc.findall('.//ns:EndToEndId', namespaces=namespace)
        for end_to_end_id in EndToEndId:
            self.assertTrue(len(end_to_end_id) <= 35)
            end_to_end_id.text = '1709565642.64888074015'
        return xml_doc
