# -*- coding: utf-8 -*-
import time

from odoo import fields
from odoo.tests.common import TransactionCase, Form

class TestItalianElectronicInvoice(TransactionCase):
    def test_state(self):
        f = Form(self.env['account.invoice'])
        f.partner_id = self.env.ref('base.res_partner_12')
        with f.invoice_line_ids.new() as l:
            l.product_id = self.env.ref('product.product_product_3')
        invoice = f.save()

        # I check that Initially customer invoice state is "Draft"
        self.assertEqual(invoice.state, 'draft')

        # I called the "Confirm Draft Invoices" wizard
        w = Form(self.env['account.invoice.confirm']).save()
        # I clicked on Confirm Invoices Button
        w.with_context(
            active_model='account.invoice',
            active_id=invoice.id,
            active_ids=invoice.ids,
            type='out_invoice',
        ).invoice_confirm()

        # I check that customer invoice state is "Open"
        self.assertEqual(invoice.state, 'open')

        # Electronic invoice must be present and have the same name as l10n_it_einvoice_name
        self.assertEqual(invoice.l10n_it_einvoice_id.name, invoice.l10n_it_einvoice_name)
