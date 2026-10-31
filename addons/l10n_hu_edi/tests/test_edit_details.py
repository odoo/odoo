# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import tagged
from odoo.tools import BinaryBytes
from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nHuEdiEditDetails(L10nHuEdiTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_income_account = cls.env['account.account'].create({
            'code': '919999',
            'name': 'Other income',
            'account_type': 'income',
        })

    def _create_sent_invoice(self):
        """ A posted invoice in the state it has after NAV confirmed it. """
        invoice = self.create_invoice_simple()
        invoice.action_post()
        invoice.write({
            'l10n_hu_edi_attachment': BinaryBytes(invoice._l10n_hu_edi_generate_xml()),
            'l10n_hu_edi_state': 'confirmed',
        })
        return invoice

    def test_edit_details_account(self):
        invoice = self._create_sent_invoice()
        with self.assertRaises(AssertionError), Form(invoice) as invoice_form:
            invoice_form.invoice_line_ids.edit(0)

        invoice.l10n_hu_edi_action_edit_details()
        self.assertTrue(invoice.l10n_hu_edi_edit_mode)
        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.account_id = self.other_income_account

        self.assertRecordValues(invoice, [{'state': 'posted', 'l10n_hu_edi_state': 'confirmed'}])
        self.assertEqual(invoice.invoice_line_ids.account_id, self.other_income_account)

        invoice.l10n_hu_edi_action_done_editing()
        self.assertFalse(invoice.l10n_hu_edi_edit_mode)
        with self.assertRaises(AssertionError), Form(invoice) as invoice_form:
            invoice_form.invoice_line_ids.edit(0)

    def test_edit_details_nav_data_locked(self):
        invoice = self._create_sent_invoice()
        invoice.l10n_hu_edi_action_edit_details()
        line = invoice.invoice_line_ids
        price_unit, name = line.price_unit, line.name

        with self.subTest(field='price_unit'), self.assertRaisesRegex(UserError, 'sent to NAV'), self.env.cr.savepoint():
            with Form(invoice) as invoice_form:
                with invoice_form.invoice_line_ids.edit(0) as line_form:
                    line_form.price_unit = price_unit + 100

        with self.subTest(field='name'), self.assertRaisesRegex(UserError, 'sent to NAV'), self.env.cr.savepoint():
            with Form(invoice) as invoice_form:
                with invoice_form.invoice_line_ids.edit(0) as line_form:
                    line_form.name = 'Another description'

        self.assertRecordValues(line, [{'price_unit': price_unit, 'name': name}])

    def test_edit_details_master_data_changed(self):
        """ Company or partner data changed since the invoice was sent: editing is still possible, only the
        changes made while editing are compared. """
        invoice = self._create_sent_invoice()
        self.company_data['company'].name = 'Renamed company'
        invoice.partner_id.vat = '14933477-2-14'

        invoice.l10n_hu_edi_action_edit_details()
        self.assertTrue(invoice.l10n_hu_edi_edit_mode)
        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.account_id = self.other_income_account
        self.assertEqual(invoice.invoice_line_ids.account_id, self.other_income_account)

        with self.assertRaisesRegex(UserError, 'sent to NAV'), self.env.cr.savepoint():
            with Form(invoice) as invoice_form:
                with invoice_form.invoice_line_ids.edit(0) as line_form:
                    line_form.price_unit += 100

        invoice.l10n_hu_edi_action_done_editing()
        self.assertRecordValues(invoice, [{'l10n_hu_edi_edit_mode': False, 'l10n_hu_edi_edit_baseline': False}])

    def test_edit_details_not_sent(self):
        invoice = self.create_invoice_simple()
        invoice.action_post()
        with self.assertRaisesRegex(UserError, 'only posted invoices sent to NAV'):
            invoice.l10n_hu_edi_action_edit_details()
