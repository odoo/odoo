# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def _get_main_company(cls):
        cls.company_data["company"].country_id = cls.env.ref("base.es").id
        cls.company_data["company"].currency_id = cls.env.ref("base.EUR").id
        cls.company_data["company"].vat = "ESA12345674"
        return cls.company_data["company"]

    def test_spanish_pos(self):
        split_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.main_pos_config.payment_method_ids = [(4, split_payment_method.id)]

        simp = self.env['account.journal'].create({
            'name': 'Simplified Invoice Journal',
            'type': 'sale',
            'company_id': self._get_main_company().id,
            'code': 'SIMP',
        })
        def get_number_of_regular_invoices():
            return self.env['account.move'].search_count([('journal_id', '=', self.main_pos_config.invoice_journal_id.id), ('l10n_es_is_simplified', '=', False), ('pos_order_ids', '!=', False)])
        initial_number_of_regular_invoices = get_number_of_regular_invoices()
        self.main_pos_config.l10n_es_simplified_invoice_journal_id = simp
        # this `limit` value is linked to the `SIMPLIFIED_INVOICE_LIMIT` const in the tour
        self.main_pos_config.l10n_es_simplified_invoice_limit = 1000
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", "spanish_pos_tour", login="pos_user")
        num_of_simp_invoices = self.env['account.move'].search_count([('journal_id', '=', simp.id), ('l10n_es_is_simplified', '=', True)])
        num_of_regular_invoices = get_number_of_regular_invoices() - initial_number_of_regular_invoices
        self.assertEqual(num_of_simp_invoices, 3)
        self.assertEqual(num_of_regular_invoices, 1)

    def test_spanish_pos_invoice_no_certificate(self):
        """This test make sure that the invoice generated in spanish PoS are not proforma invoices"""
        self.partner_a.write({
            'vat': "ESA12345674",
            'country_id': self.env.ref("base.es").id,
            'email': "email@gmail.com"
        })
        self.main_pos_config.open_ui()
        self.pos_order_pos0 = self.env['pos.order'].create({
            'company_id': self._get_main_company().id,
            'partner_id': self.partner_a.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'pricelist_id': self.main_pos_config.pricelist_id.id,
            'lines': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100,
                'qty': 1.0,
                'price_subtotal': 100,
                'price_subtotal_incl': 100,
                'discount': 0,
            })],
            'amount_total': 100,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
            'to_invoice': True,
        })

        context_make_payment = {"active_ids": [self.pos_order_pos0.id], "active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0 = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'amount': 100.0,
            'payment_method_id': self.main_pos_config.payment_method_ids[0].id,
        })
        context_payment = {'active_id': self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).check()

        self.pos_order_pos0.action_pos_order_invoice()
        attachment_proforma = self.pos_order_pos0.account_move.attachment_ids.filtered(lambda att: "proforma" in att.name)
        self.assertFalse(attachment_proforma)
        invoice_str = str(self.pos_order_pos0.account_move.get_invoice_pdf_report_attachment()[0])
        self.assertTrue("invoice" in invoice_str)
        self.assertTrue("proforma" not in invoice_str)
