# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged, new_test_user
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install", "aba_file")
class L10nPayrollAccountCommon(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()
        # Company Setup
        cls.company = cls.company_data['company']
        cls.env.user.company_ids |= cls.company
        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.resource_calendar = cls.env.ref("l10n_au_hr_payroll.resource_calendar_au_38")
        cls.resource_calendar.company_id = cls.company
        cls.company_bank_account = cls.env['res.partner.bank'].create({
            "acc_number": '12344321',
            "acc_type": 'aba',
            "aba_bsb": '123-456',
            "company_id": cls.company.id,
            "partner_id": cls.company.partner_id.id,
        })
        schedule = cls.env.ref("l10n_au_hr_payroll.structure_type_schedule_1")
        cls.default_payroll_structure = cls.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_regular')
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.bank_journal.write({
            'bank_account_id': cls.company_bank_account.id,
            "aba_fic": "CBA",
            "aba_user_spec": "Test Ltd",
            "aba_user_number": "111111",
        })
        cls.aba_ct = cls.bank_journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'aba_ct')
        cls.outbound_manual = cls.bank_journal.outbound_payment_method_line_ids.filtered(lambda l: l.code == 'manual')
        (cls.aba_ct + cls.outbound_manual).payment_account_id = cls.outbound_payment_method_line.payment_account_id

        # Employees Setup
        cls.employee_user_1 = new_test_user(cls.env, login='mel', groups='hr.group_hr_manager')
        cls.employee_contact_1 = cls.employee_user_1.partner_id
        cls.employee_contact_2 = cls.env['res.partner'].create([{
            'name': "Harry",
            'company_id': cls.env.company.id,
        }])
        cls.bank_accounts_emp_1 = cls.env['res.partner.bank'].create([{
            'acc_number': "123-666",
            'partner_id': cls.employee_contact_1.id,
            'company_id': cls.env.company.id,
            'allow_out_payment': True,
            'aba_bsb': '123456'},
            {'acc_number': "123-777",
            'partner_id': cls.employee_contact_1.id,
            'company_id': cls.env.company.id,
            'allow_out_payment': True,
            'aba_bsb': '123456'}
        ])
        cls.bank_accounts_emp_2 = cls.env['res.partner.bank'].create({
            'acc_number': "123-888",
            'partner_id': cls.employee_contact_2.id,
            'company_id': cls.env.company.id,
            'allow_out_payment': True,
            'aba_bsb': '654321'
        })
        cls.employee_1 = cls.env["hr.employee"].create({
            "name": "Mel Gibson",
            "resource_calendar_id": cls.resource_calendar.id,
            "company_id": cls.company.id,
            "user_id": cls.employee_user_1.id,
            'work_contact_id': cls.employee_contact_1.id,
            'bank_account_id': cls.bank_accounts_emp_1[1].id,
            "work_phone": "123456789",
            "private_phone": "123456789",
            "private_email": "mel@odoo.com",
            "private_street": "1 Test Street",
            "private_city": "Sydney",
            "private_state_id": cls.env.ref("base.state_au_2").id,
            "private_zip": "2000",
            "private_country_id": cls.env.ref("base.au").id,
            "birthday": date(2000, 1, 1),
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            "l10n_au_tax_free_threshold": True,
            "l10n_au_previous_payroll_id": "12312321"
        })
        cls.employee_2 = cls.env["hr.employee"].create({
            "name": "Harry Potter",
            "resource_calendar_id": cls.resource_calendar.id,
            "company_id": cls.company.id,
            'work_contact_id': cls.employee_contact_2.id,
            'bank_account_id': cls.bank_accounts_emp_2.id,
            "work_phone": "123456789",
            "private_phone": "123456789",
            "private_email": "harry@odoo.com",
            "private_street": "1 Test Street",
            "private_city": "Sydney",
            "private_state_id": cls.env.ref("base.state_au_2").id,
            "private_zip": "2000",
            "private_country_id": cls.env.ref("base.au").id,
            "birthday": date(2000, 3, 1),
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "999999661",
            "l10n_au_tax_free_threshold": True,
            "l10n_au_previous_payroll_id": "12312321"
        })
        super_fund = cls.env['l10n_au.super.fund'].create({
            'display_name': 'Fund A',
            'abn': '2345678912',
            'address_id': cls.env['res.partner'].create({'name': "Fund A Partner"}).id,
        })
        cls.env['l10n_au.super.account'].create([
            {
                "date_from": date(2023, 6, 1),
                "employee_id": cls.employee_1.id,
                "fund_id": super_fund.id
            },
            {
                "date_from": date(2023, 6, 1),
                "employee_id": cls.employee_2.id,
                "fund_id": super_fund.id
            }
        ])

        cls.contract_1 = cls.env["hr.contract"].create({
            "name": "Mel's contract",
            "employee_id": cls.employee_1.id,
            "resource_calendar_id": cls.resource_calendar.id,
            "company_id": cls.company.id,
            "date_start": date(2023, 1, 1),
            "date_end": date(2024, 5, 31),
            "wage_type": "monthly",
            "wage": 5000.0,
            "structure_type_id": schedule.id,
            "schedule_pay": "monthly",
            "state": "open"
        })
        cls.contract_2 = cls.env["hr.contract"].create({
            "name": "Harry's contract",
            "employee_id": cls.employee_2.id,
            "resource_calendar_id": cls.resource_calendar.id,
            "company_id": cls.company.id,
            "date_start": date(2023, 1, 1),
            "date_end": False,
            "wage_type": "monthly",
            "wage": 7000.0,
            "structure_type_id": schedule.id,
            "schedule_pay": "monthly",
            "state": "open"
        })
        cls.company.l10n_au_hr_super_responsible_id = cls.employee_1
        cls.company.l10n_au_stp_responsible_id = cls.employee_1
        cls.company.ytd_reset_month = "7"

    def _register_payment(self, payslip_run):
        action = payslip_run.action_register_payment()

        payment_register = (
                    self.env["account.payment.register"]
                    .with_context(
                        **action["context"],
                        hr_payroll_payment_register=True,
                        hr_payroll_payment_register_batch=payslip_run.id,
                    )
                    .create({})
                )

        return payment_register._create_payments()
