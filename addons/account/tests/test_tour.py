# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from unittest.mock import patch

import odoo.tests
from odoo import Command
from odoo.fields import Datetime as FieldDatetime

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(AccountTestInvoicingHttpCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        all_moves = cls.env['account.move'].search([('move_type', '!=', 'entry')])
        all_moves = all_moves.filtered(lambda m: not m.inalterable_hash and m.state in ('posted', 'cancel'))
        # This field is only present in account_accountant
        if 'deferred_move_ids' in all_moves._fields:
            all_moves = all_moves.filtered(lambda m: not m.deferred_move_ids)
        all_moves.button_draft()
        all_moves.with_context(force_delete=True).unlink()

        # In case of latam impacting multiple countries, disable the required fields manually.
        if 'l10n_latam_use_documents' in cls.env['account.journal']._fields:
            cls.env['account.journal']\
                .search([('company_id', '=', cls.env.company.id), ('type', '=', 'purchase')])\
                .write({'l10n_latam_use_documents': False})

    def test_01_account_tour(self):
        # Reset country and fiscal country, so that fields added by localizations are
        # hidden and non-required, and don't make the tour crash.
        # Also remove default taxes from the company and its accounts, to avoid inconsistencies
        # with empty fiscal country.
        self.env.ref('base.user_admin').write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
            'email': 'mitchell.admin@example.com',
        })
        self.env.company.write({
            'country_id': None, # Also resets account_fiscal_country_id
            'account_sale_tax_id': None,
            'account_purchase_tax_id': None,
            'external_report_layout_id': self.env.ref('web.external_layout_standard').id,
        })

        account_with_taxes = self.env['account.account'].search([('tax_ids', '!=', False), ('company_ids', '=', self.env.company.id)])
        account_with_taxes.write({
            'tax_ids': [Command.clear()],
        })

        # Remove all posted invoices to enable 'create first invoice' button
        invoices = self.env['account.move'].search([('company_id', '=', self.env.company.id), ('move_type', '=', 'out_invoice')])
        for invoice in invoices:
            if invoice.state in ('cancel', 'posted'):
                invoice.button_draft()
        invoices.unlink()

        # remove all entries in the miscellaneous journal to test the onboarding
        self.env['account.move'].search([
            ('journal_id.type', '=', 'general'),
            ('state', '=', 'draft'),
        ]).unlink()

        self.start_tour("/odoo", 'account_tour', login="admin")

    def test_01_account_tax_groups_tour(self):
        self.env.ref('base.user_admin').write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
        })
        self.env['res.partner'].create({
            'name': 'Account Tax Group Partner',
            'email': 'azure.Interior24@example.com',
        })
        product = self.env['product.product'].create({
            'name': 'Account Tax Group Product',
            'standard_price': 600.0,
            'list_price': 147.0,
            'type': 'consu',
        })
        new_tax = self.env['account.tax'].create({
            'name': '10% Tour Tax',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
        })
        product.supplier_taxes_id = new_tax

        self.start_tour("/odoo", 'account_tax_group', login="admin")

    def test_use_product_catalog_on_invoice(self):
        self.product.write({
            'is_favorite': True,
            'default_code': '0',
        })
        self.start_tour("/odoo/customer-invoices/new", 'test_use_product_catalog_on_invoice', login="admin")

    def test_deductible_amount_column(self):
        self.assertFalse(self.env.user.has_group('account.group_partial_purchase_deductibility'))
        partner = self.env['res.partner'].create({'name': "Test Partner", 'email': "test@test.odoo.com"})
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'line_ids': [Command.create({'name': "T-shirt", 'deductible_amount': 50.0})],
        })
        move.action_post()
        self.assertTrue(self.env.user.has_group('account.group_partial_purchase_deductibility'))
        self.start_tour("/odoo/vendor-bills/new", 'deductible_amount_column', login=self.env.user.login)

    def test_add_section_from_product_catalog_on_invoice_tour(self):
        self.product.write({'is_favorite': True})
        self.start_tour(
            '/odoo/customer-invoices/new',
            'test_add_section_from_product_catalog_on_invoice',
            login='admin',
        )

    def test_account_log_cancellation(self):
        invoice = self.init_invoice("out_invoice", amounts=[1000], post=True)

        def get_default_extra_edis(self, move):
            return {'edi1'}

        def get_all_extra_edis(self):
            return {
                'edi1': {'label': 'EDI 1'},
            }

        with (
            patch('odoo.addons.account.models.account_move_send.AccountMoveSend._get_default_extra_edis', get_default_extra_edis),
            patch('odoo.addons.account.models.account_move_send.AccountMoveSend._get_all_extra_edis', get_all_extra_edis)
        ):
            wizard = self.create_send_and_print(
                invoice,
                scheduled_date=FieldDatetime.to_string(self.reference_now + timedelta(days=1)),
            )
            # Process.
            with self.mock_datetime_and_now(self.reference_now):
                wizard.action_schedule_message()
            self.assertEqual(len(self._get_mail_scheduled_message(invoice, limit=None)), 1)

            # Tour: Go to the invoice and cancel the scheduled message for invoice sending.
            self.start_tour(
                f'/odoo/customer-invoices/{invoice.id}',
                'test_account_log_cancellation',
                login='accountman',
            )

        self.assertFalse(self._get_mail_scheduled_message(invoice, limit=None))
        log_note_on_cancel = self.env['mail.message'].search([
            ('model', '=', invoice._name),
            ('res_id', '=', invoice.id),
            ('body', 'ilike', '<p>The scheduled request for <strong>EDI 1</strong> is cancelled by Because I am accountman!.</p>'),
        ])
        self.assertEqual(len(log_note_on_cancel), 1)
