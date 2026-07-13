from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountBaseDocumentLayout(AccountTestInvoicingCommon):

    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_user = new_test_user(
            cls.env,
            login='account_layout_user',
            groups='account.group_account_basic',
            company_id=cls.company_data['company'].id,
        )

    def test_account_user_can_configure_document_layout(self):
        company = self.company_data['company']
        company.external_report_layout_id = False
        report_layout = self.env['report.layout'].search([], limit=1)

        layout_form = Form(self.env['base.document.layout'].with_user(self.account_user).with_company(company).with_context(
            account_document_layout_configurator=True,
        ))
        layout_form.report_layout_id = report_layout
        layout_form.report_header = 'Test invoice header'
        wizard = layout_form.save()

        wizard.document_layout_save()

        self.assertEqual(company.external_report_layout_id, report_layout.view_id)
        self.assertEqual(company.report_header, '<p>Test invoice header</p>')

    def test_configure_later_continues_send_flow_without_configuring_layout(self):
        company = self.company_data['company']
        company.external_report_layout_id = False
        report_layout = self.env['report.layout'].search([], limit=1)
        report_action = {
            'type': 'ir.actions.report',
            'context': {},
        }

        wizard = self.env['base.document.layout'].with_user(self.account_user).with_context(
            account_document_layout_configurator=True,
            can_configure_later=True,
            report_action=report_action,
        ).create({
            'company_id': company.id,
            'report_layout_id': report_layout.id,
        })

        action = wizard.action_configure_later()

        self.assertEqual(action, report_action)
        self.assertFalse(company.external_report_layout_id)
