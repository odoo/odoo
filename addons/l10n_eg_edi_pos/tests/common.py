import json
from contextlib import contextmanager
from unittest.mock import patch

from odoo.addons.point_of_sale.tests.common import CommonPosTest


class TestL10nEgEdiPosCommon(CommonPosTest):
    @classmethod
    @CommonPosTest.setup_country('eg')
    def setUpClass(cls):
        super().setUpClass()
        cls._l10n_eg_set_invoicing_threshold()
        cls._l10n_eg_create_branch_partner()
        cls._l10n_eg_create_sales_journal()
        cls._l10n_eg_create_pos_config()
        cls._l10n_eg_setup_customers()
        cls._l10n_eg_setup_eta_uom_code()
        cls._l10n_eg_create_eta_taxes()
        cls._l10n_eg_create_eta_products()
        cls._l10n_eg_enable_pos_for_eg_eta()

    # ------------------------------------------------------------------ #
    #  Setup helpers
    # ------------------------------------------------------------------ #

    @classmethod
    def _l10n_eg_set_invoicing_threshold(cls):
        cls.env.company.write({
            'l10n_eg_invoicing_threshold': 150000.0,
        })

    @classmethod
    def _l10n_eg_create_branch_partner(cls):
        """Create a fully-addressed EG branch partner with a VAT and
        all the required address fields set."""
        cls.eg_branch_partner = cls.env['res.partner'].create({
            'name': 'EG Branch',
            'vat': '111222333',
            'country_id': cls.env.ref('base.eg').id,
            'state_id': cls.env.ref('base.state_eg_c').id,
            'city': 'Cairo',
            'street': 'Tahrir 1',
            'l10n_eg_building_no': '7',
            'zip': '11511',
        })

    @classmethod
    def _l10n_eg_create_sales_journal(cls):
        """Create the EG POS sale journal carrying the required
        ETA branch / branch_id / activity code fields."""
        cls.eg_sale_journal = cls.env['account.journal'].create({
            'name': 'PoS Sale EG',
            'type': 'sale',
            'code': 'POSEG',
            'company_id': cls.company.id,
            'l10n_eg_branch_id': cls.eg_branch_partner.id,
            'l10n_eg_branch_identifier': '0',
            'l10n_eg_activity_type_id': cls.env.ref('l10n_eg_edi_eta.l10n_eg_activity_type_8121').id,
        })

    @classmethod
    def _l10n_eg_create_pos_config(cls):
        """Create a dedicated EG POS config on the EG sale journal."""
        cls.eg_cash_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Cash EG',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'journal_id': cls.env['account.journal'].create({
                'name': 'Cash EG',
                'type': 'cash',
                'company_id': cls.company.id,
            }).id,
        })
        cls.eg_pos_config = cls.env['pos.config'].create({
            'name': 'PoS Config EG',
            'journal_id': cls.eg_sale_journal.id,
            'invoice_journal_id': cls.company_data['default_journal_sale'].id,
            'payment_method_ids': [(4, cls.eg_cash_payment_method.id)],
        })

    @classmethod
    def _l10n_eg_setup_customers(cls):
        """Alias and configure the buyer fixtures used across the suite:
        - ``eg_individual_customer``: happy-path EG individual (type 'P', has VAT).
        - ``eg_business_customer``: EG business, for the ``action_pos_order_paid``
          guard that blocks sales (not refunds) to ``is_company=True`` partners.
        - ``foreign_customer``: non-EG (US) buyer; ``_l10n_eg_edi_pos_get_buyer_type``
          returns 'F' whenever country_code != 'EG', forcing id/name regardless of amount.
        - ``eg_other_customer``: unconfigured partner used only to assert the refund
          partner-mismatch guard (its only requirement is to differ from the original buyer)."""
        cls.eg_individual_customer = cls.partner_lowe
        cls.eg_individual_customer.write({
            'is_company': False,
            'country_id': cls.env.ref('base.eg').id,
            'state_id': cls.env.ref('base.state_eg_c').id,
            'city': 'Cairo',
            'street': 'Pyramid Rd 5',
            'l10n_eg_building_no': '12',
        })
        cls.eg_individual_customer._set_additional_identifier('EG_NIN', '12345678901234')
        cls.eg_business_customer = cls.partner_adgu
        cls.eg_business_customer.write({
            'vat': '999888777',
            'country_id': cls.env.ref('base.eg').id,
        })
        cls.foreign_customer = cls.partner_jcb
        cls.foreign_customer.write({
            'vat': 'US123456',
            'country_id': cls.env.ref('base.us').id,
        })
        cls.eg_other_customer = cls.partner_moda

    @classmethod
    def _l10n_eg_create_eta_taxes(cls):
        """Three ETA-classified sale taxes: VAT (T1/V009, 14%), a fixed-amount
        table tax (T3/TBL02), and one with no eta_code for the check_data
        rejection test. Tests assign these onto ``eg_product_untaxed`` inline."""
        cls.eg_tax_vat = cls.env['account.tax'].create({
            'name': 'EG VAT 14% (T1/V009)',
            'amount': 14.0,
            'l10n_eg_eta_code': 't1_v009',
        })
        cls.eg_tax_table = cls.env['account.tax'].create({
            'name': 'EG Table Tax (T3/TBL02)',
            'amount_type': 'fixed',
            'amount': 10.0,
            'l10n_eg_eta_code': 't3_tbl02',
        })
        cls.eg_tax_uncoded = cls.env['account.tax'].create({
            'name': 'EG Uncoded Tax',
            'amount': 10.0,
        })

    @classmethod
    def _l10n_eg_setup_eta_uom_code(cls):
        """Bind the existing C62 ETA UoM code to the default unit UoM."""
        cls.env.ref('uom.product_uom_unit').write({
            'l10n_eg_unit_code_id': cls.env.ref('l10n_eg_edi_eta.l10n_eg_edi_uom_code_C62').id,
        })

    @classmethod
    def _l10n_eg_create_eta_products(cls):
        """One ETA-ready POS product: item code + the unit-code UoM, no taxes.
        Tests that exercise taxes assign them onto this product inline."""
        cls.eg_product_untaxed = cls.env['product.template'].create({
            'available_in_pos': True,
            'name': 'EG ETA Product',
            'list_price': 10.0,
            'taxes_id': [(5, 0)],
            'l10n_eg_eta_code': '1KGS1TEST',
        })

    @classmethod
    def _l10n_eg_enable_pos_for_eg_eta(cls):
        """Enable ETA submission on the POS config in pre-production with dummy credentials."""
        cls.eg_pos_config.sudo().write({
            'l10n_eg_edi_pos_enable': True,
            'l10n_eg_edi_pos_preprod': True,
            'l10n_eg_edi_pos_client_id': 'test-client-id',
            'l10n_eg_edi_pos_client_secret': 'test-client-secret',
            'l10n_eg_edi_pos_serial_number': 'POS-SN-001',
        })

    # ------------------------------------------------------------------ #
    #  Order construction                                                #
    # ------------------------------------------------------------------ #

    def _create_unpaid_order(self, *, partner=None, lines=None):
        """Build a ``pos.order`` against the EG fixtures without paying it.
        The test then calls ``self._pay(order, ...)`` inside the ETA mock context
        it wants, so the EDI hook runs against a known response."""
        partner_id = (partner or self.eg_individual_customer).id
        if lines is None:
            lines = [{'product_id': self.eg_product_untaxed.product_variant_id.id, 'qty': 1.0}]
        order, _refund = self.create_backend_pos_order({
            'pos_config': self.eg_pos_config,
            'line_data': lines,
            'order_data': {'partner_id': partner_id},
        })
        return order

    def _pay(self, order):
        """Trigger ``pos.make.payment.check`` for ``order`` — this fires
        ``action_pos_order_paid``, which is the entry point the EDI hook overrides."""
        ctx = {'active_ids': order.ids, 'active_id': order.id}
        self.env['pos.make.payment'].with_context(ctx).create({
            'amount': order.amount_total,
            'payment_method_id': self.eg_cash_payment_method.id,
        }).check()

    def _refund_of(self, original):
        """Build the refund counterpart of ``original`` (unpaid).
        Mirrors what ``pos.order.refund`` does at the UI — caller still has to
        pay it under the ETA mock it wants."""
        refund_action = original.refund()
        return self.env['pos.order'].browse(refund_action['res_id'])

    # ------------------------------------------------------------------ #
    #  ETA HTTP mocking                                                  #
    # ------------------------------------------------------------------ #

    @contextmanager
    def _mock_eta(self, *, send_response=None, token='cached-token', expires_in=3600, auth_response=None):
        """Patch the single ETA HTTP entry point, dispatching on the request type
        the production code already flags. Auth requests return ``auth_response`` when
        given (use it for malformed payloads), else a well-formed
        ``{access_token, expires_in}``; submission requests return ``send_response``
        (a dict, or a callable ``(request_data) -> dict`` that inspects/echoes the
        request). The real network is never reached."""
        def fake(model_self, request_data, request_url, method, is_access_token_req=False, production_enviroment=False):
            if is_access_token_req:
                return auth_response or {'data': {'access_token': token, 'expires_in': expires_in}}
            if callable(send_response):
                return send_response(request_data)
            return send_response

        with patch.object(self.env.registry['account.edi.format'], '_l10n_eg_eta_connect_to_server', new=fake):
            yield

    @contextmanager
    def _assert_no_eta_call(self):
        """Spy the ETA HTTP entry point and assert it is never invoked."""
        with patch.object(self.env.registry['account.edi.format'], '_l10n_eg_eta_connect_to_server') as http_mock:
            yield
        self.assertFalse(http_mock.called, "Expected no ETA HTTP call")

    # ------------------------------------------------------------------ #
    #  ETA response factories                                            #
    # ------------------------------------------------------------------ #

    def _eta_accepts_any_uuid(self, *, submission_id='SUB-1'):
        """Dynamic send-response: accepts whichever uuid the order computed.
        The uuid is a SHA-256 of the payload, so tests don't know it ahead of time;
        the mock parses the request and echoes the uuid into ``acceptedDocuments``."""
        def factory(request_data):
            payload = json.loads(request_data['body'].decode())['receipts'][0]
            return {
                'ok': True,
                'data': {
                    'acceptedDocuments': [{'uuid': payload['header']['uuid']}],
                    'submissionId': submission_id,
                },
            }
        return factory

    def _eta_rejects_any_uuid(self, *, message='Validation failed'):
        """Dynamic send-response: rejects whichever uuid the order computed."""
        def factory(request_data):
            payload = json.loads(request_data['body'].decode())['receipts'][0]
            return {
                'ok': True,
                'data': {'rejectedDocuments': [{'uuid': payload['header']['uuid'], 'error': message}]},
            }
        return factory

    @staticmethod
    def _eta_response_warning(message='Transient transport error'):
        """Transport-warning shape — postprocess routes to ``to_send`` (retryable)."""
        return {'error': message, 'blocking_level': 'warning'}

    @staticmethod
    def _eta_response_error(message='Payload rejected before parsing'):
        """Transport-error shape — postprocess routes to ``error[_test]`` (non-retryable)."""
        return {'error': message, 'blocking_level': 'error'}

    @staticmethod
    def _eta_response_unknown():
        """Empty data with no accept/reject for the uuid — postprocess falls through
        to the "Unexpected response from ETA." error branch."""
        return {'ok': True, 'data': {}}

    # ------------------------------------------------------------------ #
    #  Read-back helpers                                                 #
    # ------------------------------------------------------------------ #

    def _read_envelope_json(self, order):
        """Decode the envelope attached to the order into a dict."""
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', order._name),
            ('res_id', '=', order.id),
            ('res_field', '=', 'l10n_eg_edi_pos_json_doc_file'),
        ], limit=1)
        return json.loads(attachment.raw.decode())
