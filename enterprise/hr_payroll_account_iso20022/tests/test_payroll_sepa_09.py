# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from lxml import etree

from odoo.addons.hr_payroll_account_iso20022.tests.test_payroll_sepa import TestPayrollSEPACreditTransferCommon
from odoo.tests.common import test_xsd
from odoo.tests import tagged


@tagged('external_l10n', 'post_install', '-at_install', '-standard')
class TestPayrollSEPANewCreditTransferXmlValidity(TestPayrollSEPACreditTransferCommon):
    @test_xsd(path='account_sepa/schemas/pain.001.001.09.xsd')
    def test_hr_payroll_account_iso20022_09(self):
        self.bank_journal.sepa_pain_version = 'pain.001.001.09'
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id)]
        })
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()
        self.payslip_run.action_validate()
        # make the SEPA payment.
        file = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_ids': self.payslip_run.slip_ids.ids,
            'payslip_run_id': self.payslip_run.id,
            'export_format': 'sepa',
            'journal_id': self.bank_journal.id,
        })._create_sepa_binary()

        self.assertTrue(file, 'SEPA payment has not been created!')

        sct_doc = etree.fromstring(base64.b64decode(file))

        namespaces = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.09'}
        uetr_text = sct_doc.findtext('.//ns:CdtTrfTxInf/ns:PmtId/ns:UETR', namespaces=namespaces)
        self.assertEqual(uetr_text, self.payslip_run.slip_ids.iso20022_uetr)
        return sct_doc
