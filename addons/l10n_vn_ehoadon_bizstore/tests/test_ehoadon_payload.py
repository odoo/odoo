# -*- coding: utf-8 -*-
import json

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestEhoadonPayload(TransactionCase):
    def setUp(self):
        super().setUp()
        existing = self.env['ehoadon.config'].sudo().search([], limit=1)
        if existing:
            self.config = existing
            self.config.write({
                'tax_number': '0312345678',
                'email': 'test@example.com',
                'password': 'secret',
                'tenant_id': 'tenant-demo',
                'endpoint_host': 'https://0312345678.ehoadon.net',
            })
        else:
            self.config = self.env['ehoadon.config'].sudo().create({
                'name': 'Test eHoaDon',
                'tax_number': '0312345678',
                'email': 'test@example.com',
                'password': 'secret',
                'tenant_id': 'tenant-demo',
                'endpoint_host': 'https://0312345678.ehoadon.net',
            })
        self.template = self.env['ehoadon.template'].sudo().search([('serial', '=', 'AA/26E')], limit=1)
        if not self.template:
            self.template = self.env['ehoadon.template'].sudo().create({
                'name': 'Test serial',
                'serial': 'AA/26E',
                'config_id': self.config.id,
                'payment_method': '3',
                'default_vat_rate': 10,
            })
        self.config.default_template_id = self.template

        partner = self.env['res.partner'].create({'name': 'Buyer Co'})
        product = self.env['product.product'].create({
            'name': 'Thuốc test',
            'type': 'consu',
            'list_price': 100000,
        })
        company = self.env.user.company_id
        income = (
            product.property_account_income_id
            or product.categ_id.property_account_income_categ_id
            or self.env['account.account'].search([
                ('account_type', '=', 'income'),
                ('company_ids', 'in', company.id),
            ], limit=1)
        )
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', company.id),
        ], limit=1)
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount_type', '=', 'percent'),
            ('amount', '=', 10),
            ('company_id', '=', company.id),
        ], limit=1)
        if not tax:
            tax = self.env['account.tax'].create({
                'name': 'VAT 10% test ehoadon',
                'amount': 10,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
            })

        self.move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'journal_id': journal.id,
            'ehoadon_template_id': self.template.id,
            'invoice_line_ids': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'quantity': 2,
                'price_unit': 100000,
                'tax_ids': [(6, 0, tax.ids)],
                'account_id': income.id,
            })],
        })

    def test_payload_shape(self):
        self.assertTrue(self.move.invoice_line_ids, 'invoice lines must exist')
        payload = self.move._ehoadon_generate_payload()
        self.assertEqual(payload['serial'], 'AA/26E')
        self.assertEqual(payload['paymentMethod'], 3)
        self.assertEqual(payload['currencyType'], 0)
        self.assertEqual(payload['vatRate'], 0)
        self.assertIn('eInvoiceItems', payload)
        self.assertTrue(payload['eInvoiceItems'], payload)
        item = payload['eInvoiceItems'][0]
        self.assertEqual(item['productName'], 'Thuốc test')
        self.assertEqual(item['quantity'], 2)
        self.assertEqual(item['vatRate'], 10)
        self.assertEqual(item['addAmount'], item['amount'])
        self.assertEqual(item['addVatAmount'], item['vatAmount'])
        self.assertIn('invoiceCustomer', payload)
        self.assertIn('companyName', payload['invoiceCustomer'])
        self.assertIn('taxNumber', payload['invoiceCustomer'])

    def test_header_vat_rate_follows_serial_group(self):
        self.assertEqual(self.template.vat_rate_mode, 'per_item')
        self.assertEqual(self.move._ehoadon_generate_payload()['vatRate'], 0)

        self.template.write({
            'available_serials_json': json.dumps([
                {'Value': 'AA/26E', 'Id': '1', 'Group': 'VatPerInvoice'},
                {'Value': 'BB/26E', 'Id': '2', 'Group': 'VatPerItem'},
            ]),
            'default_vat_rate': 5,
        })
        self.assertEqual(self.template.vat_rate_mode, 'per_invoice')
        self.assertEqual(self.move._ehoadon_generate_payload()['vatRate'], 5)

        self.template.write({'serial': 'BB/26E'})
        self.assertEqual(self.template.vat_rate_mode, 'per_item')
        self.assertEqual(self.move._ehoadon_generate_payload()['vatRate'], 0)

    def test_add_amount_keeps_odoo_totals_when_unit_price_rounds(self):
        """Price-included tax: rounded unit price * qty must not drive line amounts."""
        tax_incl = self.env['account.tax'].create({
            'name': 'VAT 5% incl test ehoadon',
            'amount': 5,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
            'type_tax_use': 'sale',
        })
        line = self.move.invoice_line_ids[0]
        self.move.write({'invoice_line_ids': [(1, line.id, {
            'quantity': 16,
            'price_unit': 9000,
            'tax_ids': [(6, 0, tax_incl.ids)],
        })]})
        line = self.move.invoice_line_ids[0]
        item = self.move._ehoadon_generate_payload()['eInvoiceItems'][0]
        self.assertNotEqual(item['quantity'] * item['price'], line.price_subtotal)
        self.assertEqual(item['addAmount'], line.price_subtotal)
        self.assertAlmostEqual(item['addVatAmount'], line.price_total - line.price_subtotal, places=2)
        self.assertEqual(item['addAmount'] + item['addVatAmount'], line.price_total)

    def test_vat_included_invoice_sends_odoo_totals_and_header_zero(self):
        """invoice_mtt: lines carry Odoo price_total, header must not re-apply the template rate."""
        tax_incl = self.env['account.tax'].create({
            'name': 'VAT 10% incl test ehoadon',
            'amount': 10,
            'amount_type': 'percent',
            'price_include_override': 'tax_included',
            'type_tax_use': 'sale',
        })
        line = self.move.invoice_line_ids[0]
        self.move.write({'invoice_line_ids': [(1, line.id, {
            'quantity': 1,
            'price_unit': 160000,
            'tax_ids': [(6, 0, tax_incl.ids)],
        })]})
        self.template.write({'invoice_mtt': True, 'vat_rate_mode': 'per_invoice', 'default_vat_rate': 5})
        line = self.move.invoice_line_ids[0]
        payload = self.move._ehoadon_generate_payload()
        item = payload['eInvoiceItems'][0]
        self.assertEqual(payload['vatRate'], 0)
        self.assertEqual(item['vatRate'], 0)
        self.assertEqual(item['vatAmount'], 0)
        self.assertEqual(item['price'], line.price_total)
        self.assertEqual(item['amount'], line.price_total)
        self.assertEqual(item['totalAmount'], line.price_total)
        self.assertEqual(item['addAmount'], line.price_total)

    def test_single_rate_resplits_mixed_lines_at_template_rate(self):
        """VatPerInvoice 5%: lines at 0/5/10/no tax keep Odoo totals, re-split at 5%."""
        Tax = self.env['account.tax']
        taxes = [
            Tax.create({'name': 'VAT %s%% test single' % rate, 'amount': rate,
                        'amount_type': 'percent', 'type_tax_use': 'sale'})
            for rate in (0, 5)
        ]
        base_line = self.move.invoice_line_ids[0]
        self.move.write({'invoice_line_ids': [
            (1, base_line.id, {'quantity': 3, 'price_unit': 123457}),
            (0, 0, {'name': 'Phí khám', 'quantity': 1, 'price_unit': 97273,
                    'account_id': base_line.account_id.id, 'tax_ids': [(6, 0, taxes[0].ids)]}),
            (0, 0, {'name': 'Thuốc 5%', 'quantity': 7, 'price_unit': 33333,
                    'account_id': base_line.account_id.id, 'tax_ids': [(6, 0, taxes[1].ids)]}),
            (0, 0, {'name': 'Không thuế', 'quantity': 1, 'price_unit': 55555,
                    'account_id': base_line.account_id.id, 'tax_ids': [(5, 0, 0)]}),
        ]})
        self.template.write({'invoice_mtt': False, 'vat_rate_mode': 'per_invoice', 'default_vat_rate': 5})

        payload = self.move._ehoadon_generate_payload()
        items = payload['eInvoiceItems']
        total = self.move.amount_total
        self.assertEqual(payload['vatRate'], 5)
        self.assertEqual(len(items), 4)
        self.assertTrue(all(item['vatRate'] == 5 for item in items), items)
        self.assertTrue(all(item['amount'] + item['vatAmount'] == item['totalAmount'] for item in items))
        self.assertAlmostEqual(sum(item['totalAmount'] for item in items), total, places=2)
        untaxed = sum(item['amount'] for item in items)
        self.assertEqual(untaxed, self.move.currency_id.round(total / 1.05))
        self.assertAlmostEqual(untaxed * 1.05, total, delta=1)
        last = items[-1]
        self.assertEqual(last['price'], self.move.currency_id.round(last['amount'] / last['quantity']))

    def test_phase2_paths_and_business_payload(self):
        online_add = self.config.ehoadon_path('add', template=self.template)
        self.assertIn('EInvoiceOnline/AddEInvoice', online_add)
        self.template.is_cash_register = True
        cash_add = self.config.ehoadon_path('add', template=self.template)
        cash_pub = self.config.ehoadon_path('publish', template=self.template)
        self.assertIn('CashRegister/AddEInvoice', cash_add)
        self.assertIn('CashRegister/SendToTaxAuthority', cash_pub)
        self.template.is_cash_register = False

        origin = self.move.copy()
        origin.ehoadon_invoice_id = 'origin-inv'
        self.move.ehoadon_business_type = 'replace'
        self.move.ehoadon_origin_move_id = origin.id
        from odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_payload_builder import (
            EhoadonPayloadBuilder,
            INVOICE_TYPE_REPLACE,
        )
        body = EhoadonPayloadBuilder(self.move).build_business(
            INVOICE_TYPE_REPLACE, 'origin-inv',
        )
        self.assertEqual(body['originalInvoiceId'], 'origin-inv')
        self.assertEqual(body['invoiceType'], INVOICE_TYPE_REPLACE)
        self.assertIn('eInvoiceItems', body['invoice'])

    def test_business_payload_has_no_origin_note_row(self):
        """eHoaDon prints the replace/adjust reference itself; items are only the product lines."""
        from odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_payload_builder import (
            EhoadonPayloadBuilder,
            INVOICE_TYPE_ADJUSTED_DOWN,
            INVOICE_TYPE_REPLACE,
        )
        builder = EhoadonPayloadBuilder(self.move)
        product_items = builder.build()['eInvoiceItems']
        for invoice_type in (INVOICE_TYPE_REPLACE, INVOICE_TYPE_ADJUSTED_DOWN):
            items = builder.build_business(invoice_type, 'origin-inv')['invoice']['eInvoiceItems']
            self.assertEqual(len(items), len(product_items))
            self.assertFalse(any(item.get('explain') for item in items))

    def test_replacement_requires_group(self):
        group = self.env.ref('l10n_vn_ehoadon_bizstore.group_ehoadon_send_replacement')
        self.move.ehoadon_business_type = 'replace'
        self.env.user.group_ids -= group
        with self.assertRaisesRegex(UserError, 'quyền phát hành hóa đơn thay thế'):
            self.move._ehoadon_add_or_business(self.template)
        self.env.user.group_ids |= group
        # Past the permission gate: fails on the missing origin invoice instead.
        with self.assertRaisesRegex(UserError, 'hóa đơn gốc'):
            self.move._ehoadon_add_or_business(self.template)

    def test_base_url(self):
        url = self.config.api_url('Api/EInvoiceOnline/AddEInvoice')
        self.assertEqual(
            url,
            'https://0312345678.ehoadon.net/Api/EInvoiceOnline/AddEInvoice',
        )

    def test_token_and_send_mocked(self):
        """HTTP mocked — verifies auth header + Add + Publish paths."""
        calls = []

        class FakeResp:
            def __init__(self, payload, status=200):
                self._payload = payload
                self.status_code = status
                self.reason = 'OK'
                self.text = ''

            def json(self):
                return self._payload

        def fake_request(method, url, json=None, headers=None, timeout=None):
            calls.append({'method': method, 'url': url, 'json': json, 'headers': headers or {}})
            if 'Token/Create' in url or 'token/create' in url.lower():
                return FakeResp({
                    'status': 'success',
                    'code': 200,
                    'data': {
                        'accessToken': 'tok-test',
                        'accessTokenExpiredAt': '2099-01-01T00:00:00Z',
                    },
                })
            if 'AddEInvoice' in url:
                return FakeResp({
                    'status': 'success',
                    'code': 200,
                    'data': {
                        'invoiceId': 'inv-1',
                        'guid': 'g-1',
                        'lookupCode': 'LKP',
                        'viewUrl': 'https://example/look',
                        'errors': {},
                    },
                })
            if 'PublishInvoice' in url:
                return FakeResp({'status': 'success', 'code': 200, 'data': {}})
            return FakeResp({'status': 'error', 'message': 'unexpected %s' % url}, status=400)

        import odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_config as cfg_mod
        old = cfg_mod.requests.request
        cfg_mod.requests.request = fake_request
        try:
            self.env.user.group_ids |= self.env.ref('l10n_vn_ehoadon_bizstore.group_ehoadon_send_invoice')
            self.move.action_post()
            self.move.action_ehoadon_send_invoice()
        finally:
            cfg_mod.requests.request = old

        urls = [c['url'] for c in calls]
        self.assertTrue(any('Token/Create' in u for u in urls), urls)
        create_calls = [c for c in calls if 'Token/Create' in c['url']]
        self.assertTrue(create_calls)
        body = create_calls[0]['json']
        self.assertEqual(body.get('Email'), 'test@example.com')
        self.assertEqual(body.get('TenantId'), 'tenant-demo')
        self.assertIn('Password', body)
        self.assertTrue(any('0312345678.ehoadon.net' in u for u in urls), urls)
        self.assertTrue(any('AddEInvoice' in u for u in urls), urls)
        self.assertTrue(any('PublishInvoice' in u for u in urls), urls)
        self.assertEqual(self.move.ehoadon_invoice_id, 'inv-1')
        self.assertEqual(self.move.ehoadon_invoice_state, 'sent')
        auth_headers = [
            c['headers'].get('Authorization')
            for c in calls
            if 'AddEInvoice' in c['url'] or 'PublishInvoice' in c['url']
        ]
        self.assertTrue(all(h == 'Bearer tok-test' for h in auth_headers), auth_headers)

    def _run_preview_ensure(self, responder):
        """Call _ehoadon_ensure_invoice_id_for_pdf with HTTP mocked; returns list of (method, url)."""
        calls = []

        class FakeResp:
            status_code = 200
            reason = 'OK'
            text = ''

            def __init__(self, payload):
                self._payload = payload

            def json(self):
                return self._payload

        def fake_request(method, url, json=None, headers=None, timeout=None):
            calls.append((method, url))
            if 'Token/Create' in url:
                return FakeResp({'status': 'success', 'data': {
                    'accessToken': 'tok', 'accessTokenExpiredAt': '2099-01-01T00:00:00Z',
                }})
            return FakeResp(responder(method, url))

        import odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_config as cfg_mod
        old = cfg_mod.requests.request
        cfg_mod.requests.request = fake_request
        try:
            self.move._ehoadon_ensure_invoice_id_for_pdf(self.template)
        finally:
            cfg_mod.requests.request = old
        return [c for c in calls if 'Token/Create' not in c[1]]

    def test_preview_refreshes_unissued_draft(self):
        self.move.write({
            'ehoadon_invoice_id': 'inv-old',
            'ehoadon_invoice_number': '00000000',
            'ehoadon_invoice_state': 'error',
        })
        calls = self._run_preview_ensure(
            lambda method, url: {'status': 'success', 'data': {'InvoiceId': 'inv-old', 'Errors': {}}},
        )
        self.assertEqual(len(calls), 1, calls)
        self.assertIn('EInvoiceOnline/UpdateEInvoice', calls[0][1])
        self.assertEqual(self.move.ehoadon_invoice_id, 'inv-old')
        self.assertEqual(self.move.ehoadon_invoice_state, 'draft_remote')

    def test_preview_recreates_draft_from_other_channel(self):
        self.move.write({
            'ehoadon_invoice_id': 'inv-cash',
            'ehoadon_invoice_number': '00000000',
            'ehoadon_invoice_state': 'draft_remote',
        })

        def responder(method, url):
            if 'EInvoiceOnline/UpdateEInvoice' in url:
                return {'status': 'error', 'data': {'Errors': {'EInvoice': 'Không tìm thấy hóa đơn'}}}
            if 'EInvoiceOnline/DeleteEInvoice' in url:
                return {'status': 'error', 'message': 'einvoicce.delete.notfound'}
            if 'CashRegister/DeleteEInvoice' in url:
                return {'status': 'success', 'message': ''}
            if 'EInvoiceOnline/AddEInvoice' in url:
                return {'status': 'success', 'data': {'InvoiceId': 'inv-new', 'Errors': {}}}
            return {'status': 'error', 'message': 'unexpected %s' % url}

        calls = self._run_preview_ensure(responder)
        urls = [u for _m, u in calls]
        self.assertTrue(any('CashRegister/DeleteEInvoice/inv-cash' in u for u in urls), urls)
        self.assertIn('EInvoiceOnline/AddEInvoice', urls[-1])
        self.assertEqual(self.move.ehoadon_invoice_id, 'inv-new')
        self.assertEqual(self.move.ehoadon_invoice_state, 'draft_remote')

    def test_update_payload_omits_placeholder_invoice_number(self):
        self.move.write({'ehoadon_invoice_id': 'inv-1', 'ehoadon_invoice_number': '00000000'})
        self.assertNotIn('invoiceNumber', self.move._ehoadon_generate_payload(include_remote_ids=True))
        self.move.ehoadon_invoice_number = '00000005'
        self.assertEqual(
            self.move._ehoadon_generate_payload(include_remote_ids=True)['invoiceNumber'], '00000005',
        )

    def test_preview_leaves_issued_invoice_untouched(self):
        self.move.write({
            'ehoadon_invoice_id': 'inv-issued',
            'ehoadon_invoice_number': '00000005',
            'ehoadon_invoice_state': 'sent',
        })
        calls = self._run_preview_ensure(lambda method, url: {'status': 'error'})
        self.assertEqual(calls, [])
        self.assertEqual(self.move.ehoadon_invoice_id, 'inv-issued')

    def test_send_request_accepts_int_status(self):
        """Regression: API may return status as int HttpStatusCode, not string."""
        class FakeResp:
            status_code = 200
            reason = 'OK'
            text = ''

            def json(self):
                return {
                    'status': 200,
                    'code': 200,
                    'data': {
                        'accessToken': 'tok-int',
                        'accessTokenExpiredAt': '2099-01-01T00:00:00Z',
                    },
                }

        import odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_config as cfg_mod
        old = cfg_mod.requests.request
        cfg_mod.requests.request = lambda *a, **k: FakeResp()
        try:
            token, error = self.config.get_access_token(force_refresh=True)
        finally:
            cfg_mod.requests.request = old
        self.assertFalse(error, error)
        self.assertEqual(token, 'tok-int')

    def test_token_create_plain_jwt_body(self):
        """Token/Create returns bare JWT text/plain, not JSON envelope."""
        jwt = (
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
            'eyJFbWFpbCI6ImFwaUBlaG9hZG9uLm9ubGluZSJ9.'
            'signature'
        )

        class FakeResp:
            status_code = 200
            reason = 'OK'
            text = jwt
            headers = {'content-type': 'text/plain; charset=utf-8'}

            def json(self):
                raise ValueError('not json')

        import odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_config as cfg_mod
        old = cfg_mod.requests.request
        cfg_mod.requests.request = lambda *a, **k: FakeResp()
        try:
            token, error = self.config.get_access_token(force_refresh=True)
        finally:
            cfg_mod.requests.request = old
        self.assertFalse(error, error)
        self.assertEqual(token, jwt)

    def test_get_token_button_uses_template_mst(self):
        calls = []

        class FakeResp:
            status_code = 200
            reason = 'OK'
            text = ''

            def json(self):
                return {
                    'status': 'success',
                    'data': {
                        'accessToken': 'tok-btn',
                        'accessTokenExpiredAt': '2099-01-01T00:00:00Z',
                    },
                }

        def fake_request(method, url, json=None, headers=None, timeout=None):
            calls.append({'url': url, 'json': json})
            return FakeResp()

        self.template.write({
            'email': 'api@ehoadon.online',
            'password': 'secret',
            'tenant_id': '5d1a348028069517e0d6f4aa',
            'tax_number': '0123456789',
        })
        import odoo.addons.l10n_vn_ehoadon_bizstore.models.ehoadon_config as cfg_mod
        old = cfg_mod.requests.request
        cfg_mod.requests.request = fake_request
        try:
            self.template.action_get_token()
        finally:
            cfg_mod.requests.request = old

        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0]['url'],
            'https://0123456789.ehoadon.net/Api/Token/Create',
        )
        self.assertEqual(calls[0]['json']['Email'], 'api@ehoadon.online')
        self.assertEqual(calls[0]['json']['TenantId'], '5d1a348028069517e0d6f4aa')
        self.assertEqual(self.template.access_token, 'tok-btn')
