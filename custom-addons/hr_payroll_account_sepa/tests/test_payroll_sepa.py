# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from datetime import datetime, timedelta
from lxml import etree

from odoo.fields import Date
from odoo.addons.hr_payroll_account.tests.test_hr_payroll_account import TestHrPayrollAccountCommon
from odoo.tests import common, tagged
from odoo.tools.misc import file_path


@tagged('post_install', '-at_install')
class TestPayrollSEPACreditTransfer(TestHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollSEPACreditTransfer, cls).setUpClass()
        cls.env.company.currency_id = cls.env.ref('base.USD')
        cls.env.user.company_id.write({
            'sepa_orgid_id': "0468651441",
            'country_id': cls.env.ref('base.us').id,
        })

        cls.bank = cls.env['res.bank'].create({
            'name':'BNP',
            'bic': 'GEBABEBB',
        })

        cls.res_partner_bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE32707171912447',
            'partner_id': cls.work_contact.id,
            'acc_type': 'bank',
            'bank_id': cls.bank.id,
        })

        cls.bank_partner = cls.env['res.partner.bank'].create({
            'acc_number' : 'BE84567968814145',
            'acc_type': 'iban',
            'partner_id': cls.env.ref('base.main_company').partner_id.id,
        })

        cls.hr_employee_john.bank_account_id = cls.res_partner_bank

        cls.bank_journal = cls.env['account.journal'].create({
            'name' : 'Bank',
            'code' : 'BNK',
            'type' : 'bank',
            'bank_id' : cls.bank.id,
            'bank_account_id': cls.bank_partner.id,
        })

        # Get a pain.001.001.03 schema validator
        schema_file_path = file_path('account_sepa/schemas/pain.001.001.03.xsd')
        cls.xmlschema = etree.XMLSchema(etree.parse(schema_file_path))

    def test_00_hr_payroll_account_sepa(self):
        """ Checking the process of payslip when you create a SEPA payment. """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I make the SEPA payment.
        self.hr_payslip_john._create_xml_file(self.bank_journal)

        # I verify if a file is created.
        self.assertTrue(self.hr_payslip_john.sepa_export, 'SEPA payment has not been created!')

        # I verify the xml.
        sct_doc = etree.fromstring(base64.b64decode(self.hr_payslip_john.sepa_export))
        self.assertTrue(self.xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)

        # I verify the payslip is in paid state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State should not change!')

    def test_01_hr_payroll_account_sepa(self):
        """ Checking the process of payslip run when you create a SEPA payment. """

        # I verify the payslip run is in draft state.
        self.assertEqual(self.payslip_run.state, 'draft', 'State not changed!')

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm the payslip run.
        self.payslip_run.action_validate()

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I make the SEPA payment.
        self.payslip_run.mapped('slip_ids')._create_xml_file(self.bank_journal)

        # I verify if a file is created for the payslip run.
        self.assertTrue(self.payslip_run.sepa_export, 'SEPA payment has not been created!')

        # I verify the xml.
        sct_doc = etree.fromstring(base64.b64decode(self.payslip_run.sepa_export))
        self.assertTrue(self.xmlschema.validate(sct_doc), self.xmlschema.error_log.last_error)

        # I verify the payslip is in paid state.
        self.assertEqual(self.payslip_run.state, 'close', 'State should not change!')
