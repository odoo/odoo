# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import json
from unittest import mock
import contextlib
import requests
import logging
import time

from odoo import Command, fields
from odoo.tools.misc import file_open
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.base.models.ir_cron import ir_cron

_logger = logging.getLogger(__name__)


class TestKeEdiCommon(TestAccountMoveSendCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.is_live_test = False
        cls.parent_cmc_key = os.getenv('KE_PARENT_CMC_KEY', 'cmc_key')
        cls.branch_cmc_key = os.getenv('KE_BRANCH_CMC_KEY', 'cmc_key')

        cls.company_data['company'].write({
            'vat': 'P052112956W',
            'l10n_ke_branch_code': '00',
            'l10n_ke_server_mode': 'test',
            'l10n_ke_oscu_cmc_key': cls.parent_cmc_key,
            'l10n_ke_oscu_user_agreement': True,
        })

        # 20 * (seconds since epoch) modulo 2^31-1 is a pretty good initializer that leaves space for 20 invoices
        # and also happens to fit in an int32. Note that 2^31 - 1 is a prime number! ;)
        cls.sale_sequence_number = (int(time.time()) * 10) % (2**31 - 1)

        cls.partner_a.write({
            'name': 'Ralph Jr',
            'street': 'The Cucumber Lounge',
            'city': 'Vineland',
            'zip': '00500',
            'country_id': cls.env.ref('base.ke').id,
            'vat': 'A000123456F',
        })

        cls.standard_rate_sales_tax = cls.env['account.chart.template'].ref('ST16')
        cls.standard_rate_purchase_tax = cls.env['account.chart.template'].ref('PT16')
        cls.reduced_rate_sales_tax = cls.env['account.chart.template'].ref('ST8')
        cls.reduced_rate_purchase_tax = cls.env['account.chart.template'].ref('PT8')

        cls.product_service = cls.env['product.product'].create([{
            'name': 'Fiscal Optimization Consultancy',
            'type': 'service',
            'taxes_id': [Command.set(cls.standard_rate_sales_tax.ids)],
            'supplier_taxes_id': [Command.set(cls.standard_rate_purchase_tax.ids)],
            'standard_price': 100.0,
            'l10n_ke_product_type_code': '3',
            'l10n_ke_origin_country_id': cls.env.ref('base.ke').id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '81121500'),
            ], limit=1).id,
            'l10n_ke_packaging_unit_id': cls.env.ref('l10n_ke_edi_oscu.code_17_OU').id,
            'l10n_ke_packaging_quantity': 1,
        }])

        currency_eur = cls.env.ref('base.EUR')
        currency_eur.active = True
        cls.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'currency_id': currency_eur.id,
            'company_id': cls.company_data['company'].id,
            'inverse_company_rate': '100.00',
        })

        cls.excise_tax = cls.env['account.tax'].create({
            'name': 'Excise tax',
            'amount_type': 'percent',
            'amount': 30.0,
            'country_id': cls.company_data['company'].account_fiscal_country_id.id,
            'tax_exigibility': 'on_invoice',
            'price_include_override': 'tax_included',
            'include_base_amount': True,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                }),
            ],
        })

    def _test_create_branches(self):
        parent = self.company_data['company']
        parent.action_l10n_ke_create_branches()
        branches = self.env['res.company'].search([('parent_id', '=', parent.id)])

        self.assertTrue(branches[0].name.startswith('KAKAMEGA'))
        self.assertTrue(branches[1].name.startswith('MOMBASA'))

        expected_branches = [
            {
                'vat': 'P052112956W',
                'l10n_ke_branch_code': '02',
            },
            {
                'vat': 'P052112956W',
                'l10n_ke_branch_code': '01',
            },
        ]
        self.assertRecordValues(branches, expected_branches)

        for branch in branches:
            branch.write({'country_id': self.env.ref('base.ke')})
            (self.product_a | self.product_b).with_company(branch).write({'standard_price': 30})

    @contextlib.contextmanager
    def patch_session(self, responses):
        """ Patch requests.Session in l10n_ke_edi_oscu/models/company.py """

        def replace_ignore(dict_to_replace):
            """ Replace `___ignore___` in the expected request JSONs by unittest.mock.ANY,
                which is equal to everything. """
            for k, v in dict_to_replace.items():
                if v == '___ignore___':
                    dict_to_replace[k] = mock.ANY
            return dict_to_replace

        self.maxDiff = None
        test_case = self
        json_module = json

        responses = iter(responses)

        class MockedSession:
            def __init__(self):
                self.headers = {}

            def post(self, url, json=None, timeout=None):
                expected_service, expected_request_filename, response_filename = next(responses)
                _, _, service = url.rpartition('/')

                test_case.assertEqual(service, expected_service)

                stock_services = (
                    'insertStockIO',
                    'saveStockMaster',
                    'selectImportItemList',
                    'selectItemList',
                    'updateImportItem',
                )

                module = 'l10n_ke_edi_oscu_stock' if service in stock_services else 'l10n_ke_edi_oscu'

                with file_open(f'{module}/tests/expected_requests/{expected_request_filename}.json', 'rb') as expected_request_file:
                    try:
                        test_case.assertEqual(json_module.loads(expected_request_file.read(), object_hook=replace_ignore), json)
                    except AssertionError:
                        _logger.error('Unexpected request JSON for service %s', service)
                        raise

                mock_response = mock.Mock(spec=requests.Response)
                mock_response.status_code = 200
                mock_response.headers = ''

                with file_open(f'{module}/tests/mocked_responses/{response_filename}.json', 'rb') as response_file:
                    mock_response.content = response_file.read()
                    mock_response.text = mock_response.content.decode()

                mock_response.json.side_effect = lambda: json_module.loads(mock_response.content)

                return mock_response

        with mock.patch('odoo.addons.l10n_ke_edi_oscu.models.res_company.requests.Session', side_effect=MockedSession, autospec=True) as mock_session:
            yield mock_session

        try:
            next(responses)
        except StopIteration:
            pass
        else:
            test_case.fail('Not all expected calls were made!')

    @contextlib.contextmanager
    def patch_cron_trigger(self):
        """ Decorator for patching ir.cron.trigger so that the cron gets run right after this context manager's exit. """
        crons_to_trigger = []

        def mock_trigger(cron, at=None):
            crons_to_trigger.append(cron)

        with mock.patch.object(ir_cron, '_trigger', side_effect=mock_trigger, autospec=True) as mocked_trigger:
            yield mocked_trigger

        # Run cron as current user (not superuser) to limit ourselves to the test company
        self.env.invalidate_all()
        self.env['ir.cron'].union(*crons_to_trigger).ir_actions_server_id.run()

    def create_reversal(self, invoice, is_modify=False):
        """ Create a credit note that reverses an invoice. """
        wizard_vals = {'journal_id': invoice.journal_id.id}
        wizard_reverse = self.env['account.move.reversal'].with_context(active_ids=invoice.ids, active_model='account.move').create(wizard_vals)
        wizard_reverse.write({
            'reason': 'Return',
            'l10n_ke_reason_code_id': self.env.ref('l10n_ke_edi_oscu.code_32_06').id,
        })
        wizard_reverse.reverse_moves(is_modify=is_modify)
        return wizard_reverse.new_move_ids

    @classmethod
    @contextlib.contextmanager
    def set_invoice_number(cls, invoice):
        if not invoice.is_sale_document():
            raise NotImplementedError('`set_invoice_number` is only needed for out_invoice / out_refund!')
        sequence = invoice._l10n_ke_get_invoice_sequence()
        sequence.number_next_actual = cls.sale_sequence_number
        try:
            yield
        finally:
            cls.sale_sequence_number = sequence.number_next
