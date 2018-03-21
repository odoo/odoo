import logging
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestMulticompanyFlow(TransactionCase):

    def with_context(self, *args, **kwargs):
        context = dict(args[0] if args else self.env.context, **kwargs)
        self.env = self.env(context=context)
        return self

    def _get_templates(self):
        ir_model_data = self.env['ir.model.data']

        account_template_data_1 = ir_model_data.search(
            [('name', '=', 'transfer_account_id')], limit=1)
        account_template_data_2 = ir_model_data.search(
            [('name', '=', 'conf_a_recv')], limit=1)
        account_template_data_3 = ir_model_data.search(
            [('name', '=', 'conf_a_pay')], limit=1)

        account_template_1 = self.env['account.account.template'].browse(
            [account_template_data_1.res_id])
        account_template_2 = self.env['account.account.template'].browse(
            [account_template_data_2.res_id])
        account_template_3 = self.env['account.account.template'].browse(
            [account_template_data_3.res_id])

        tax_template_data_1 = ir_model_data.search(
            [('name', '=', 'sale_tax_template')], limit=1)
        tax_template_data_2 = ir_model_data.search(
            [('name', '=', 'purchase_tax_template')], limit=1)

        account_tax_template_1 = self.env['account.tax.template'].browse(
            [tax_template_data_1.res_id])
        account_tax_template_2 = self.env['account.tax.template'].browse(
            [tax_template_data_2.res_id])

        res = [account_template_1, account_template_2, account_template_3,
               account_tax_template_1, account_tax_template_2]
        return res

    def _chart_of_accounts_create(self, company, chart, templates):
        _logger.debug('Creating chart of account')

        templates[0].chart_template_id = chart
        templates[1].chart_template_id = chart
        templates[2].chart_template_id = chart

        if templates[3].company_id:
            templates[3].company_id = company
        if templates[4].company_id:
            templates[4].company_id = company

        chart.tax_template_ids |= templates[3]
        chart.tax_template_ids |= templates[4]

        self.env.user.write({
            'company_ids': [(4, company.id)],
            'company_id': company.id,
        })
        wizard = self.with_context(
            company_id=company.id, force_company=company.id
        ).env['wizard.multi.charts.accounts'].create({
            'company_id': company.id,
            'chart_template_id': chart.id,
            'code_digits': 6,
            'currency_id': self.env.ref('base.EUR').id,
            'transfer_account_id': chart.transfer_account_id.id,
            'sale_tax_id': chart.tax_template_ids.filtered(
                lambda t: t.type_tax_use == 'sale').id,
            'purchase_tax_id': chart.tax_template_ids.filtered(
                lambda t: t.type_tax_use == 'purchase').id,
        })
        wizard.onchange_chart_template_id()
        wizard.execute()
        return True

    post_install = True
    at_install = False

    def setUp(self):
        super(TestMulticompanyFlow, self).setUp()
        self.account_model = self.env['account.account']
        self.account_template_model = self.env['account.account.template']
        self.chart_template_model = self.env['account.chart.template']
        self.invoice_model = self.env['account.invoice']
        self.invoice_line_model = self.env['account.invoice.line']
        self.journal_model = self.env['account.journal']
        self.payment_model = self.env['account.payment']
        self.reg_payment_model = self.env['account.register.payments']

        employees_group = self.env.ref('base.group_user')
        partner_manager_group = self.env.ref('base.group_partner_manager')
        multi_company_group = self.env.ref('base.group_multi_company')
        account_user_group = self.env.ref('account.group_account_user')
        account_manager_group = self.env.ref('account.group_account_manager')

        # Create companies
        self.company = self.env['res.company'].create({
            'name': 'Test company 1',
        })
        self.company_2 = self.env['res.company'].create({
            'name': 'Test company 2',
            'parent_id': self.company.id
        })

        # Create charts for both companies
        templates = self._get_templates()
        self.chart = self.env['account.chart.template'].create({
            'name': 'Test Chart',
            'currency_id': self.env.ref('base.EUR').id,
            'transfer_account_id': templates[0].id,
            'property_account_receivable_id': templates[1].id,
            'property_account_payable_id': templates[2].id,
        })
        self._chart_of_accounts_create(self.company, self.chart, templates)
        self.chart.company_id = self.company

        self.chart_2 = self.env['account.chart.template'].create({
            'name': 'Test Chart 2',
            'currency_id': self.env.ref('base.EUR').id,
            'transfer_account_id': templates[0].id,
            'property_account_receivable_id': templates[1].id,
            'property_account_payable_id': templates[2].id,
        })
        self._chart_of_accounts_create(self.company_2, self.chart_2, templates)
        self.chart_2.company_id = self.company_2

        # create an user with account full rights
        self.user = self.env['res.users'].sudo().with_context(
            no_reset_password=True).create(
            {'name': 'Test User',
             'login': 'test_user',
             'email': 'test@odoo.com',
             'groups_id': [(6, 0, [employees_group.id,
                                   partner_manager_group.id,
                                   account_user_group.id,
                                   account_manager_group.id,
                                   multi_company_group.id,
                                   ])],
             'company_id': self.company.id,
             'company_ids': [(6, 0, [self.company.id, self.company_2.id])],
             })

        self.user_type_1 = self.env.ref('account.data_account_type_receivable')
        self.user_type_2 = self.env.ref('account.data_account_type_revenue')
        self.manual_payment = self.env.ref(
            'account.account_payment_method_manual_in')

        # other data
        self.partner = self.env['res.partner'].sudo(self.user).create({
            'name': 'Partner Test',
            'company_id': False,
            'is_company': True,
        })
        self.account_1 = self.account_model.sudo(self.user).create({
            'name': 'Account 1 - Test',
            'code': 'account_1',
            'user_type_id': self.user_type_1.id,
            'company_id': self.company_2.id,
            'reconcile': True,
        })
        self.account_2 = self.account_model.sudo(self.user).create({
            'name': 'Account 2 - Test',
            'code': 'account_2',
            'user_type_id': self.user_type_2.id,
            'company_id': self.company_2.id,
        })
        self.cash_journal = self.journal_model.sudo(self.user).create({
            'name': 'Cash Journal - Test',
            'code': 'test_cash',
            'type': 'cash',
            'company_id': self.company_2.id,
        })

        self.invoice = self.invoice_model.sudo(self.user).create({
            'partner_id': self.partner.id,
            'journal_id': self.cash_journal.id,
            'account_id': self.account_1.id,
            'company_id': self.company_2.id,
            'type': 'out_invoice',
        })
        self.invoice_line = self.invoice_line_model.sudo(self.user).create({
            'name': 'Line test',
            'account_id': self.account_2.id,
            'invoice_id': self.invoice.id,
            'price_unit': 1.0,
            'quantity': 1.0,
        })

    def test_pay_an_invoice_from_a_different_company_01(self):
        """User (in company_1) creates invoice (in company_2)
        and register a payment through 'Register Payment' button"""
        self.assertEqual(self.invoice_line.company_id.id, self.company_2.id)

        self.invoice.action_invoice_open()
        self.assertEqual(self.invoice.company_id.id, self.company_2.id)

        self.reg_payment = self.payment_model.with_context(
            default_company_id=self.company_2.id,
            default_invoice_ids=[(4, self.invoice.id, None)]
        ).sudo(self.user).create({
                'amount': 1.0,
                'payment_type': 'inbound',
                'payment_method_id': self.manual_payment.id,
                'journal_id': self.cash_journal.id,
            })
        self.assertEqual(self.reg_payment.company_id.id, self.company_2.id)

        self.reg_payment.action_validate_invoice_payment()
        self.assertEqual(self.reg_payment.company_id.id, self.company_2.id)

    def test_pay_an_invoice_from_a_different_company_02(self):
        """User (in company_1) creates an invoice (in company_2)
        and register a payment through 'Register Payment' Action"""
        self.assertEqual(self.invoice_line.company_id.id, self.company_2.id)

        self.invoice.action_invoice_open()
        self.assertEqual(self.invoice.company_id.id, self.company_2.id)

        self.wiz_reg_payment = self.reg_payment_model.with_context(
            active_ids=[self.invoice.id]).sudo(self.user).create({
                'amount': 1.0,
                'payment_type': 'inbound',
                'payment_method_id': self.manual_payment.id,
                'journal_id': self.cash_journal.id,
            })
        self.assertEqual(self.wiz_reg_payment.company_id.id, self.company_2.id)

        view_dict = self.wiz_reg_payment.create_payments()
        self.reg_payment = self.payment_model.search(view_dict['domain'])
        self.assertEqual(self.reg_payment.company_id.id, self.company_2.id)
