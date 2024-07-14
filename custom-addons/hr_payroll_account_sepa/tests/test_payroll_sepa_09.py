# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from lxml import etree

from odoo.addons.hr_payroll_account_sepa.tests.test_payroll_sepa import TestPayrollSEPACreditTransfer
from odoo.tests import tagged
from odoo.tools.misc import file_path


@tagged('post_install', '-at_install')
class TestPayrollSEPANewCreditTransfer(TestPayrollSEPACreditTransfer):

    def test_hr_payroll_account_sepa_09(self):
        self.bank_journal.sepa_pain_version = 'pain.001.001.09'
        schema_file_path = file_path('account_sepa/schemas/pain.001.001.09.xsd')
        xmlschema = etree.XMLSchema(etree.parse(schema_file_path))

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id)]
        })
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()
        self.payslip_run.action_validate()
        # make the SEPA payment.
        self.payslip_run.mapped('slip_ids')._create_xml_file(self.bank_journal)

        self.assertTrue(self.payslip_run.sepa_export, 'SEPA payment has not been created!')

        # verify the xml.
        sct_doc = etree.fromstring(base64.b64decode(self.payslip_run.sepa_export))
        self.assertTrue(xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)

        namespaces = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.09'}
        uetr_text = sct_doc.findtext('.//ns:CdtTrfTxInf/ns:PmtId/ns:UETR', namespaces=namespaces)
        self.assertEqual(uetr_text, self.payslip_run.slip_ids.sepa_uetr)
