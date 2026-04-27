from unittest.mock import patch
from freezegun import freeze_time

from .common import TestL10nCoEdiPosCommon

from odoo import Command
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_co_edi_pos.models.pos_order import PosOrder


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDianPosUbl(TestL10nCoEdiPosCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.config.company_id.write({
            'l10n_co_dian_test_environment': True,
            'l10n_co_dian_certification_process': True,
        })

    def setUp(self):
        super().setUp()
        # reset the dian naming sequence because it will increase with every testcase
        journal = self.config.l10n_co_edi_final_consumer_invoices_journal_id
        journal.l10n_co_edi_pos_sequence_id.number_next = journal.l10n_co_edi_min_range_number

        # reset pos order sequence because it will increase with every testcase
        self.config.sequence_id.number_next = 1

    def _assert_dian_pos_order_xml(self, pos_order_line_ui_args, payments, expected_xml_file_name, tip_amount=None):
        # 1. Assert PoS order
        pos_order_ui_data = {
            'pos_order_lines_ui_args': pos_order_line_ui_args,
            'payments': payments,
        }
        original_send_function = PosOrder.l10n_co_edi_pos_action_send_document

        def apply_tip(order):
            """Analog to set_tip() in point_of_sale/pos_store.js"""

            order.is_tipped = True
            order.tip_amount = tip_amount  # the default tip amount
            order._compute_prices()  # re-compute the prices with the applied tip

        def wrapper(self):
            if tip_amount:
                apply_tip(self)
            original_send_function(self)

        with patch.object(PosOrder, 'l10n_co_edi_pos_action_send_document', new=wrapper):
            order = self._create_and_send_order(pos_order_ui_data=pos_order_ui_data, response_file_name='SendTestSetAsync.xml')

        pos_order_xml, errors = self.env['pos.edi.xml.ubl_dian']._export_pos_order(order)

        self.assertFalse(errors)

        with file_open(f'l10n_co_edi_pos/tests/expected_xmls/{expected_xml_file_name}.xml', 'rb') as f:
            expected_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(pos_order_xml),
            self.get_xml_tree_from_string(expected_xml),
        )

        # 2. Assert invoice created from PoS order
        with (
            self._pos_session(),
            self._mock_get_status(),
            self._disable_get_acquirer_call(),
            patch(f'{self.utils_path}._build_and_send_request', return_value=self._mocked_response('SendTestSetAsync.xml', 200)),
        ):
            extra_data = {}
            if tip_amount:
                extra_data = {
                    'is_tipped': True,
                    'tip_amount': tip_amount,
                }

            order_with_move = self._create_order(
                ui_data={
                    **pos_order_ui_data,
                    'is_invoiced': True,
                    'customer': self.partner_co,
                },
                extra_data=extra_data,
            )

        invoice = order_with_move.account_move
        invoice_xml, errors = self.env['account.edi.xml.ubl_dian']._export_invoice(invoice)

        self.assertFalse(errors)

        with file_open(f'l10n_co_edi_pos/tests/expected_xmls/{expected_xml_file_name}_invoice.xml', 'rb') as f:
            expected_invoice_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(invoice_xml),
            self.get_xml_tree_from_string(expected_invoice_xml),
        )

        return order, order_with_move

    @freeze_time('2025-03-01')
    def test_10_pos_order(self):
        self._assert_dian_pos_order_xml(
            pos_order_line_ui_args=[(self.product_a, 2)],
            payments=[(self.default_pos_payment_method, 2380.0)],
            expected_xml_file_name='pos_order',
        )

    @freeze_time('2025-03-01')
    def test_20_pos_order_withholding_taxes(self):
        withholding_tax = self.env["account.chart.template"].ref('l10n_co_tax_56')
        self.product_a.taxes_id += withholding_tax

        self._assert_dian_pos_order_xml(
            pos_order_line_ui_args=[(self.product_a, 2)],
            payments=[(self.default_pos_payment_method, 2323.0)],
            expected_xml_file_name='pos_order_withholding_taxes',
        )

    @freeze_time('2025-03-01')
    def test_30_pos_order_sugar_taxes(self):
        self.product_sugar_1.write({
            'taxes_id': [Command.set([self.tax_iva_5.id, self.sugar_tax_1.id])],
        })
        self.product_sugar_2.write({
            'taxes_id': [Command.set([self.tax_iva_5.id, self.sugar_tax_2.id])],
        })
        self._assert_dian_pos_order_xml(
            pos_order_line_ui_args=[(self.product_sugar_1, 2), (self.product_sugar_2, 3)],
            payments=[(self.default_pos_payment_method, 2563.25)],
            expected_xml_file_name='pos_order_sugar_taxes',
        )

    @freeze_time('2025-03-01')
    def test_40_pos_order_tips(self):
        # Enable tips in settings
        self.config.iface_tipproduct = True
        self.config.tip_product_id.taxes_id = False  # force no taxes on the tip product

        # Tips are not taxed and have their own allowance charge vals
        self._assert_dian_pos_order_xml(
            pos_order_line_ui_args=[(self.product_a, 1), (self.config.tip_product_id, 1)],
            payments=[(self.default_pos_payment_method, 1191.0)],
            expected_xml_file_name='pos_order_tips',
            tip_amount=1.0,
        )

    @freeze_time('2025-03-01')
    def test_50_pos_order_refund(self):
        _, order_with_move = self._assert_dian_pos_order_xml(
            pos_order_line_ui_args=[(self.product_a, 2)],
            payments=[(self.default_pos_payment_method, 2380.0)],
            expected_xml_file_name='pos_order',
        )

        # Makes sure the cufe is set on the move
        self._mock_send_and_print(move=order_with_move.account_move, response_file='SendTestSetAsync.xml')
        self._mock_get_status_zip(move=order_with_move.account_move, response_file='GetStatusZip_warnings.xml')

        with self._pos_session():
            refund_order = order_with_move._refund()
            credit_note = refund_order._create_invoice(refund_order._prepare_invoice_vals())
            credit_note.reversed_entry_id = order_with_move.account_move

        credit_note.action_post()
        credit_note_xml, errors = self.env['account.edi.xml.ubl_dian']._export_invoice(credit_note)

        self.assertFalse(errors)

        with file_open('l10n_co_edi_pos/tests/expected_xmls/pos_order_credit_note.xml', 'rb') as f:
            expected_invoice_xml = f.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(credit_note_xml),
            self.get_xml_tree_from_string(expected_invoice_xml),
        )
