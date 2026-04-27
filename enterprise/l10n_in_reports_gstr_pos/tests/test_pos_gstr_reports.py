# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from datetime import date
from freezegun import freeze_time

from odoo.fields import Command

from .common import TestInGstrPosBase
from .gstr_test_json import expected_gstr1_pos_response, expected_gstr1_pos_response_old_period, expected_gstr1_pos_response_current_period, expected_pos_service_product_gstr1_response

TEST_DATE = date(2023, 5, 20)


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestInGstrPosGSTR(TestInGstrPosBase):
    """
    Test class for GSTR-related POS functionality.
    """

    @freeze_time('2023-05-20')
    def test_gstr1_json_generation_with_pos_refund_order(self):
        """Test case for partial refund and GSTR1 JSON generation."""
        with self.with_pos_session() as session:
            # Step 1: Create an order with two products
            order = self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_a, 2.0),  # Buying 2 units of product_a
                    (self.product_b, 2.0),  # Buying 2 units of product_b
                ],
                'payments': [(self.bank_pm1, 630.0)],  # Payment of 630
            })

            # Step 2: Create a refund for one product line
            self._create_order({
                'pos_order_lines_ui_args': [
                    {
                        'product': self.product_b,
                        'quantity': -1.0,  # Refund 1 unit of product_b
                        'refunded_orderline_id': order.lines[1].id,
                    },
                ],
                'payments': [(self.bank_pm1, -210.0)],  # Refund of 210
            })

            # Step 3: Close POS session and generate GSTR1 report
            session.action_pos_session_closing_control()

            # Step 4: Create GSTR1 report and compare JSON output
            gstr1_report = self.env['l10n_in.gst.return.period'].create({
                'company_id': self.company_data["company"].id,
                'periodicity': 'monthly',
                'year': TEST_DATE.strftime('%Y'),
                'month': TEST_DATE.strftime('%m'),
            })
            gstr1_json = gstr1_report._get_gstr1_json()

            # Assert GSTR1 JSON matches the expected data
            self.assertDictEqual(gstr1_json, expected_gstr1_pos_response)

    @freeze_time('2023-05-20')
    def test_gstr1_json_of_previous_period_updated_after_invoice_generated_in_later_month(self):
        """Ensure GSTR-1 JSON for previous period is updated after reversal in current period."""
        # Step 1: Setup partner details
        self.partner_a.write({
            'vat': '24ABCPM8965E1ZE',
            'state_id': self.env.ref("base.state_in_gj").id,
        })

        # Step 2: Create POS orders under old return period (April)
        old_return_period_date = date(2023, 4, 19)
        with freeze_time(old_return_period_date):
            with self.with_pos_session():
                self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product_a, 2.0),
                        (self.product_b, 2.0),
                    ],
                    'payments': [(self.bank_pm1, 630.0)],
                })
                going_to_invoice_order_in_next_session = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product_a, 2.0),
                        (self.product_b, 2.0),
                    ],
                    'payments': [(self.bank_pm1, 630.0)],
                    'customer': self.partner_a,
                })

        # Step 3: Generate and verify old GSTR1
        old_return_period = self.env['l10n_in.gst.return.period'].create({
            'company_id': self.company_data["company"].id,
            'periodicity': 'monthly',
            'year': old_return_period_date.strftime('%Y'),
            'month': old_return_period_date.strftime('%m'),
        })
        old_return_period_json = old_return_period._get_gstr1_json()
        self.assertDictEqual(old_return_period_json, expected_gstr1_pos_response_old_period)

        # Step 4: Generate invoice for old order in current period
        going_to_invoice_order_in_next_session._generate_pos_order_invoice()

        # Step 5: Generate and verify current GSTR1
        current_gstr1_report = self.env['l10n_in.gst.return.period'].create({
            'company_id': self.company_data["company"].id,
            'periodicity': 'monthly',
            'year': TEST_DATE.strftime('%Y'),
            'month': TEST_DATE.strftime('%m'),
        })
        current_gstr1_report_json = current_gstr1_report._get_gstr1_json()
        self.assertDictEqual(current_gstr1_report_json, expected_gstr1_pos_response_current_period)

        # Step 6: Re-generate and verify updated old GSTR1 JSON
        updated_old_return_period_json = old_return_period._get_gstr1_json()
        self.assertDictEqual(updated_old_return_period_json, expected_gstr1_pos_response_old_period)

    @freeze_time('2023-05-20')
    def test_gstr1_service_product_json_generation(self):
        # Create a service-type product with GST tax (5%) and HSN code
        product_service = self.env['product.product'].create({
            'name': 'Service Product',
            'type': 'service',
            'lst_price': 100.0,
            'taxes_id': [Command.set(self.gst_5.ids)],  # Apply 5% GST tax
            'l10n_in_hsn_code': '9911',  # HSN code for services
        })

        with self.with_pos_session():
            self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_a, 2.0),       # Buying 2 units of product_a
                    (product_service, 2.0),      # Buying 2 units of service product
                ],
                'payments': [(self.bank_pm1, 420.0)],  # Payment amount of 420
            })

        # Generate a new GSTR1 return period for the given company and date
        gstr1_report = self.env['l10n_in.gst.return.period'].create({
            'company_id': self.company_data["company"].id,
            'periodicity': 'monthly',
            'year': TEST_DATE.strftime('%Y'),
            'month': TEST_DATE.strftime('%m'),
        })

        # Generate GSTR1 JSON from the report
        gstr1_json = gstr1_report._get_gstr1_json()

        # Assert GSTR1 JSON matches the expected data
        self.assertDictEqual(gstr1_json, expected_pos_service_product_gstr1_response)
