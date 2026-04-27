# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import re
from contextlib import contextmanager
from unittest import mock
from unittest.mock import patch

from odoo import Command
from odoo.addons.l10n_br_avatax.models.account_external_tax_mixin import AccountExternalTaxMixinL10nBR
from odoo.addons.l10n_br_edi.tests.test_l10n_br_edi import TestL10nBREDICommon
from odoo.addons.l10n_br_edi_pos.models.pos_order import PosOrder
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged, freeze_time
from odoo.tools import file_open
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization

# All tested POS orders are mocked to use this ID when calculating the access key
TEST_POS_ORDER_ID = 548
TEST_DATETIME = "2025-02-05T22:55:17+00:00"


class TestL10nBREDIPOSCommon(TestL10nBREDICommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_screens.available_in_pos = True
        cls.company.write(
            {
                "l10n_br_edi_csc_number": "00001",
                "l10n_br_edi_csc_identifier": "000000000000000000000000000000000000",
                "l10n_br_avatax_api_identifier": "TEST",
                "l10n_br_avatax_api_key": "TEST",
                "vat": "49233848000150",
            }
        )

    @contextmanager
    def _with_mocked_l10n_br_iap_request(self, expected_communications):
        """Checks that we send the right requests and returns corresponding mocked responses. Heavily inspired by
        patch_session in l10n_ke_edi_oscu."""
        self.maxDiff = None
        test_case = self
        json_module = json
        expected_communications = iter(expected_communications)

        ignored_new_fields = {}
        if self.env['ir.module.module']._get('l10n_br_edi_fiscal_reform').state == 'installed':
            ignored_new_fields = {
                'header.goods': 'enableCalcICBS',
                'header.locations.entity.taxesSettings': 'notCbsIbsTaxPayer',
                'header.locations.establishment.taxesSettings': 'notCbsIbsTaxPayer',
                'lines': 'goods',
                'lines.itemDescriptor': 'unit',
            }

        def mocked_l10n_br_iap_request(self, route, json=None, company=None):
            def add_new_fields(d, path):
                updated = {}
                # lines and summary are replaced with the tax response when submitting the invoice
                if (route == 'calculate_tax' or 'lines' not in path) and (new_field := ignored_new_fields.get(".".join(path))):
                    updated[new_field] = mock.ANY

                for k, v in d.items():
                    new_path = path + [k]

                    if isinstance(v, dict):
                        updated[k] = add_new_fields(v, new_path)
                    elif isinstance(v, list):
                        updated[k] = [add_new_fields(el, new_path) for el in v]
                    else:
                        updated[k] = v

                return updated

            def replace_ignore(dict_to_replace):
                """Replace `___ignore___` in the expected request JSONs by unittest.mock.ANY,
                which is equal to everything."""
                for k, v in dict_to_replace.items():
                    if v == "___ignore___":
                        dict_to_replace[k] = mock.ANY
                return dict_to_replace

            expected_route, expected_request_filename, expected_response_filename = next(expected_communications)
            test_case.assertEqual(route, expected_route)

            with file_open(f"l10n_br_edi_pos/tests/mocked_requests/{expected_request_filename}.json", "r") as request_file:
                expected_request = json_module.loads(request_file.read(), object_hook=replace_ignore)
                test_case.assertEqual(
                    json,
                    expected_request,
                    f"Expected request did not match actual request for route {route}.",
                )

            with file_open(f"l10n_br_edi_pos/tests/mocked_responses/{expected_response_filename}.json", "r") as response_file:
                api_response = json_module.loads(response_file.read())

                if expected_route == "calculate_tax":
                    expected_lines = api_response["lines"]
                    lines = self.lines
                    test_case.assertEqual(
                        len(lines), len(expected_lines), f"The sent order was expected to have {len(expected_lines)} lines."
                    )

                    # Set the line IDs in the mocked response to the line IDs of this order.
                    for i, line in enumerate(expected_lines):
                        line["lineCode"] = lines[i].id

                return api_response

        with patch(
            f"{AccountExternalTaxMixinL10nBR.__module__}.AccountExternalTaxMixinL10nBR._l10n_br_iap_request",
            autospec=True,
            side_effect=mocked_l10n_br_iap_request,
        ), patch(
            f"{PosOrder.__module__}.PosOrder._l10n_br_get_id_for_cnf", autospec=True, side_effect=lambda *args: TEST_POS_ORDER_ID
        ):
            yield

        if next(expected_communications, None):
            self.fail("Not all expected calls were made!")


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBREDIPOS(TestL10nBREDIPOSCommon, TestPointOfSaleCommon):
    def setUp(self):
        super().setUp()
        self.pos_config.write(
            {
                "l10n_br_is_nfce": True,
                "l10n_br_invoice_serial": "1",
            }
        )

        self.pos_config.open_ui()
        self.session = self.pos_config.current_session_id

    def _create_simple_order(self):
        return self.PosOrder.create(
            {
                "name": "Order/0001",
                "session_id": self.session.id,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product_screens.product_variant_id.id,
                            "qty": 3,
                            "price_unit": 1.0,
                            "price_subtotal": 3.0,
                            "price_subtotal_incl": 3.0,
                        }
                    )
                ],
                "amount_tax": 0.0,
                "amount_total": 3.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
            }
        )

    def test_01_access_key_check_digit(self):
        self.assertEqual(
            self.env["pos.order"]._l10n_br_calculate_access_key_check_digit("4323070738511100010255503000765973124086659"),
            3,
        )

    @freeze_time(TEST_DATETIME)
    def test_02_session_closing(self):
        order = self._create_simple_order()
        with self._with_mocked_l10n_br_iap_request(
            [
                ("calculate_tax", "anonymous_tax_request", "anonymous_tax_response"),
                ("submit_invoice_goods", "anonymous_edi_request", "anonymous_edi_response"),
            ]
        ):
            self.env["pos.make.payment"].with_context(active_id=order.id).create({"amount": order.amount_total}).check()

        self.session.action_pos_session_close()
        self.assertEqual(self.session.state, "closed", "Session should be closed without differences.")

    def _test_adjustment_entry(self, order, expected_communications, expected_adjustment_line_vals):
        order.l10n_br_last_avatax_status = "error"
        self.env["pos.make.payment"].with_context(active_id=order.id).create({"amount": order.amount_total}).check()
        self.session.action_pos_session_close()
        self.assertEqual(self.session.state, "closed", "Session should be closed without differences.")

        with self._with_mocked_l10n_br_iap_request(expected_communications):
            order.button_l10n_br_edi()

        adjustment_entry = self.env["account.move"].search([("ref", "like", order.name)])
        self.assertEqual(len(adjustment_entry), 1, f"There should be one adjustment journal entry for {order.name}.")
        self.assertRecordValues(
            adjustment_entry.line_ids,
            expected_adjustment_line_vals,
        )

    @freeze_time(TEST_DATETIME)
    def test_03_edi_after_session_closed_simple(self):
        """Verify that a correcting journal entry is created if EDI is successfully retried after the session is closed."""
        order = self._create_simple_order()
        expected_communications = [
            ("calculate_tax", "anonymous_tax_request", "anonymous_tax_response"),
            ("submit_invoice_goods", "anonymous_edi_request", "anonymous_edi_response"),
        ]
        expected_adjustment_line_vals = [
            {
                "account_id": order.lines.product_id._get_product_accounts()["income"].id,
                "amount_currency": 0.58,
            },
            {
                "account_id": self.env["account.account"].search([("code", "=", "2.01.01.09.05")]).id,  # cofins
                "amount_currency": 0.00,
            },
            {
                "account_id": self.env["account.account"].search([("code", "=", "2.01.01.09.03")]).id,  # icms
                "amount_currency": -0.58,
            },
            {
                "account_id": self.env["account.account"].search([("code", "=", "2.01.01.09.04")]).id,  # pis
                "amount_currency": 0.00,
            },
        ]
        self._test_adjustment_entry(
            order,
            expected_communications,
            expected_adjustment_line_vals,
        )

    @freeze_time(TEST_DATETIME)
    def test_04_edi_after_session_closed_complex(self):
        """Verify the correcting journal entry posted after EDI is successfully retried in a closed session. Uses
        an order with multiple products that have different income accounts."""
        other_income_account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.company),
                ("account_type", "=", "income"),
                ("id", "!=", self.company_data["default_account_revenue"].id),
            ],
            limit=1,
        )
        self.product_cabinet.property_account_income_id = other_income_account
        order = self.PosOrder.create(
            {
                "name": "Order/0002",
                "session_id": self.session.id,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product_screens.product_variant_id.id,
                            "qty": 3,
                            "price_unit": 1.0,
                            "price_subtotal": 3.0,
                            "price_subtotal_incl": 3.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_cabinet.product_variant_id.id,
                            "qty": 5,
                            "price_unit": 3.0,
                            "price_subtotal": 15.0,
                            "price_subtotal_incl": 15.0,
                        }
                    ),
                ],
                "amount_tax": 0.0,
                "amount_total": 18.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
            }
        )
        expected_communications = [
            ("calculate_tax", "anonymous_tax_request_multiple_lines", "anonymous_tax_response_multiple_lines"),
            ("submit_invoice_goods", "anonymous_edi_request_multiple_lines", "anonymous_edi_response_multiple_lines"),
        ]
        expected_adjustment_line_vals = [
            {
                "account_id": self.product_screens._get_product_accounts()["income"].id,
                "amount_currency": 0.58,
            },
            {
                "account_id": other_income_account.id,
                "amount_currency": 2.93,
            },
            {
                "account_id": self.env["account.account"].search([("code", "=", "2.01.01.09.05")]).id,  # cofins
                "amount_currency": 0.00,
            },
            {
                "account_id": self.env["account.account"].search([("code", "=", "2.01.01.09.03")]).id,  # icms
                "amount_currency": -3.51,
            },
            {
                "account_id": self.env["account.account"].search([("code", "=", "2.01.01.09.04")]).id,  # pis
                "amount_currency": 0.00,
            },
        ]
        self._test_adjustment_entry(
            order,
            expected_communications,
            expected_adjustment_line_vals,
        )

    @freeze_time(TEST_DATETIME)
    def test_05_order_messages(self):
        order = self._create_simple_order()
        with self._with_mocked_l10n_br_iap_request(
            [
                ("calculate_tax", "anonymous_tax_request", "anonymous_tax_response"),
                ("submit_invoice_goods", "anonymous_edi_request", "anonymous_edi_response"),
            ]
        ):
            self.env["pos.make.payment"].with_context(active_id=order.id).create({"amount": order.amount_total}).check()

        self.assertRegex(order.message_ids[-2].body, ".*E-invoice submitted successfully.*")
        self.assertRegex(
            order.message_ids[-1].body,
            f".*{re.escape('<b>aa Regular Consumable Product</b><br>COFINS Incl. - R$&nbsp;0.00<br>ICMS Incl. - R$&nbsp;0.58<br>PIS Incl. - R$&nbsp;0.00')}.*"
        )

    @freeze_time(TEST_DATETIME)
    def test_06_order_no_payments(self):
        """ POS Orders with no payments due to 0 cost should always have paymentMode sent otherwise
            Avalara will error."""
        order = self.PosOrder.create(
            {
                "name": "Order/0001",
                "session_id": self.session.id,
                "lines": [
                    Command.create(
                        {
                            "product_id": self.product_screens.product_variant_id.id,
                            "qty": 3,
                            "price_unit": 0.0,
                            "price_subtotal": 0.0,
                            "price_subtotal_incl": 0.0,
                        },
                    ),
                ],
                "amount_tax": 0.0,
                "amount_total": 0.0,
                "amount_paid": 0.0,
                "amount_return": 0.0,
            },
        )

        payload = order._l10n_br_get_calculate_payload()
        expected_dict = {
            'paymentInfo': {
                'paymentMode': [
                    {
                        "mode": "99",
                        "value": 0.0,
                        "modeDescription": "Other",
                    },
                ],
            },
        }
        self.assertDictEqual(payload['header']['payment'], expected_dict, 'paymentMode should still be set for free orders!')


@freeze_time(TEST_DATETIME)
@tagged("post_install_l10n", "post_install", "-at_install")
class TestUi(TestL10nBREDIPOSCommon, TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.write(
            {
                "l10n_br_is_nfce": True,
                "l10n_br_invoice_serial": "1",
            }
        )
        cls.main_pos_config.payment_method_ids.write({"l10n_br_payment_method": "01"})
        cls.product_screens.write(
            {
                "list_price": 1.0,
                "taxes_id": False,
            }
        )
        cls.product_cabinet.write(
            {
                "taxes_id": cls.env["account.tax"].create(
                    {"name": "Excluded Tax", "amount": 10.0, "price_include_override": "tax_excluded"}
                ),
                "available_in_pos": True,
            }
        )

    def setUp(self):
        super().setUp()
        self.main_pos_config.sequence_id.number_next_actual = 1  # the mocked requests expect orders to be the first

    def test_01_anonymous_order(self):
        with self._with_mocked_l10n_br_iap_request(
            [
                ("calculate_tax", "anonymous_tax_request", "anonymous_tax_response"),
                ("submit_invoice_goods", "anonymous_edi_request", "anonymous_edi_response"),
            ]
        ):
            self.start_tour(
                "/pos/ui?config_id=%d" % self.main_pos_config.id,
                "l10n_br_edi_pos.tour_anonymous_order",
                login=self.env.user.login,
            )

    def test_02_customer_order(self):
        with self._with_mocked_l10n_br_iap_request(
            [
                ("calculate_tax", "customer_tax_request", "customer_tax_response"),
                ("submit_invoice_goods", "customer_edi_request", "customer_edi_response"),
            ]
        ):
            self.start_tour(
                "/pos/ui?config_id=%d" % self.main_pos_config.id, "l10n_br_edi_pos.tour_customer_order", login=self.env.user.login
            )

            order = self.env['pos.order'].search([], limit=1, order='id desc')
            self.assertEqual(order.is_invoiced, False)

    def test_03_company_order(self):
        self.partner_customer.company_type = 'company'

        with self._with_mocked_l10n_br_iap_request(
            [
                ("calculate_tax", "company_tax_request", "company_tax_response"),
                ("submit_invoice_goods", "company_edi_request", "company_edi_response"),
            ]
        ):
            self.start_tour(
                "/pos/ui?config_id=%d" % self.main_pos_config.id, "l10n_br_edi_pos.tour_customer_order", login=self.env.user.login
            )

            order = self.env['pos.order'].search([], limit=1, order='id desc')
            self.assertEqual(order.is_invoiced, False)


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericBR(TestGenericLocalization, TestL10nBREDIPOSCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('br')
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.company_id.name = 'Company BR'
        cls.main_pos_config.write(
            {
                "l10n_br_is_nfce": True,
                "l10n_br_invoice_serial": "1",
            }
        )
        cls.wall_shelf.write({
            'taxes_id': False,
        })
        cls.whiteboard_pen.write({
            'taxes_id': False
        })
