import odoo.tests
from odoo import Command
from odoo.addons.website.tools import MockRequest
from odoo.addons.point_of_sale.tests.common import archive_products
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient
from odoo.addons.pos_urban_piper.controllers.main import PosUrbanPiperController
from unittest.mock import patch

from datetime import datetime, timedelta


@odoo.tests.tagged('post_install', '-at_install')
class TestPosUrbanPiperCommon(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.env['ir.config_parameter'].set_param('pos_urban_piper.urbanpiper_username', 'demo')
        cls.env['ir.config_parameter'].set_param('pos_urban_piper.urbanpiper_apikey', 'demo')
        cls.urban_piper_config = cls.env['pos.config'].create({
            'name': 'Urban Piper',
            'module_pos_urban_piper': True,
            'urbanpiper_delivery_provider_ids': [Command.set([cls.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id])]
        })
        cls.product_1 = cls.env['product.template'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'taxes_id': [(5, 0, 0)],
            'type': 'consu',
            'list_price': 100.0,
        })
        cls.discount_product = cls.env['product.product'].create({
            'name': 'Merchant Discount',
            'default_code': 'MRDT',
            'taxes_id': [(5, 0, 0)],
            'type': 'consu',
        })
        cls.up_controller = PosUrbanPiperController()
        cls.MockRequest = staticmethod(MockRequest)

    def _test_order_json(self, data):
        taxes = data['product_id'].taxes_id.compute_all(
            data['product_id'].list_price, data['product_id'].currency_id, data['quantity']
        )
        unit_price = data['product_id'].taxes_id.compute_all(
            data['product_id'].list_price, data['product_id'].currency_id, 1
        )['total_excluded']
        price_with_tax = taxes['total_included']
        price_without_tax = taxes['total_excluded']
        delivery_datetime = data['delivery_datetime']
        payload = {
            "customer": {
                "username": "meet_jivani",
                "name": "Meet Jivani",
                "id": 1111111,
                "phone": "+919999999999",
                "address": {
                    "is_guest_mode": False,
                    "city": "Gujarat",
                    "pin": "380007",
                    "line_1": "401 & 402, Floor 4, IT Tower 3",
                    "line_2": "InfoCity Gate, 1, Gandhinagar,",
                    "sub_locality": "Test Area"
                },
                "email": "test_user@email.com"
            },
            "order": {
                "next_states": ["Acknowledged", "Food Ready", "Dispatched", "Completed", "Cancelled"],
                "items": [{
                    "food_type": data['product_id'].urbanpiper_meal_type,
                    "total": price_without_tax,
                    "id": 1111111,
                    "title": data['product_id'].name,
                    "total_with_tax": price_with_tax,
                    "discounts": [],
                    "tags": [],
                    "price": unit_price,
                    "discount": 0.0,
                    "merchant_id": f'{data["product_id"].id}-XXXXX',
                    "instructions": "",
                    "charges": [],
                    "extras": {},
                    "image_url": None,
                    "total_charge": 0.0,
                    "is_recommended": False,
                    "quantity": data['quantity']
                }],
                "details": {
                    "coupon": "",
                    "total_taxes": price_with_tax - price_without_tax,
                    "merchant_ref_id": None,
                    "order_level_total_charges": 0,
                    "id": data['delivery_identifier'],
                    "payable_amount": price_with_tax,
                    "total_external_discount": 0.0,
                    "order_total": price_with_tax,
                    "expected_pickup_time": int((datetime.now() + timedelta(minutes=25)).timestamp() * 1000),
                    "state": "Placed",
                    "discount": 0.0,
                    "channel": data['delivery_provider_id'].technical_name,
                    "delivery_datetime": int((datetime.now() + timedelta(minutes=delivery_datetime)).timestamp() * 1000),
                    "item_level_total_charges": 0,
                    "item_taxes": 0.0,
                    "modified_to": None,
                    "item_level_total_taxes": price_with_tax - price_without_tax,
                    "order_state": "Placed",
                    "instructions": "Test order instructions",
                    "created": int(datetime.now().timestamp() * 1000),
                    "charges": [],
                    "country": "India",
                    "biz_name": "Odoo_IN",
                    "taxes": [],
                    "prep_time": {
                        "max": 85.0,
                        "adjustable": True,
                        "estimated": 25.0,
                        "min": 0.0
                    },
                    "ext_platforms": [{
                        "kind": "food_aggregator",
                        "name": data['delivery_provider_id'].technical_name,
                        "delivery_type": "partner",
                        "extras": {
                            "order_otp": "4175",
                            "deliver_asap": True,
                            "is_delivery_charge_discounted": False,
                            "can_reject_order": True,
                        },
                        "platform_store_id": "6546563516",
                        "id": "MNHLAW3L"
                    }],
                    "order_level_total_taxes": 0,
                    "order_subtotal": price_without_tax * data['quantity'],
                },
                "payment": [{
                    "amount": price_with_tax,
                    "option": "payment_gateway",
                    "srvr_trx_id": None
                }],
                "store": {
                    "city": "Gandhinagar",
                    "name": "Odoo India",
                    "merchant_ref_id": data['config_id'].urbanpiper_store_identifier,
                    "address": "401 & 402, Floor 4, IT Tower 3 InfoCity Gate, 1, Gandhinagar, Gujarat 382007",
                    "id": 11111
                },
                "next_state": "Acknowledged",
                "urban_piper_test": True,
            }
        }
        charges = []
        if data['packaging_charge'] > 0:
            charges.append({
                'taxes': [
                    {
                        'rate': None,
                        'liability_on': 'aggregator',
                        'value': (data['packaging_charge'] * 15) / 100,
                        'title': 'VAT'
                    }
                ] if data['has_tax'] else [],
                'value': data['packaging_charge'],
                'title': 'Packaging Charge'
            })
        if data['delivery_charge'] > 0:
            charges.append({
                'taxes': [
                    {
                        'rate': None,
                        'liability_on': 'aggregator',
                        'value': (data['delivery_charge'] * 15) / 100,
                        'title': 'VAT'
                    }
                ] if data['has_tax'] else [],
                'value': data['delivery_charge'],
                'title': 'Delivery Charge'
            })
        payload["order"]["details"]["charges"] = charges
        discounts = []
        if data['discount_amount'] > 0:
            discounts.append({
                'is_merchant_discount': True,
                'code': 'CRICKET',
                'value': data['discount_amount'],
                'title': 'Merchant Discount'
            })
        payload['order']['details']['ext_platforms'][0]['discounts'] = discounts
        if data['delivery_instruction']:
            payload['order']['details']['instructions'] = data['delivery_instruction']
        return payload

    def make_test_order(self, order_data):
        data = {
            'config_id': order_data.get('config_id'),
            'product_id': order_data.get('product_id'),
            'quantity': order_data.get('quantity') or 1,
            'discount_amount': order_data.get('discount_amount') or 0,
            'packaging_charge': order_data.get('packaging_charge') or 0,
            'delivery_charge': order_data.get('delivery_charge') or 0,
            'delivery_instruction': order_data.get('delivery_instruction'),
            'delivery_provider_id': order_data.get('delivery_provider_id'),
            'delivery_identifier': order_data.get('delivery_identifier'),
            'has_tax': order_data.get('has_tax', True),
            'delivery_datetime': order_data.get('delivery_datetime') or 25
        }
        order_json = self._test_order_json(data=data)
        UpController = self.up_controller
        UpController._create_order(order_json)


class TestFrontend(TestPosUrbanPiperCommon):

    def test_payment_method_close_session(self):
        def _mock_make_api_request(self, endpoint, method='POST', data=None, timeout=10):
            return []
        self.urban_piper_config.payment_method_ids = self.env['pos.payment.method'].search([]).filtered(lambda pm: pm.type == 'bank')
        with patch.object(UrbanPiperClient, "_make_api_request", _mock_make_api_request):
            self.urban_piper_config.with_user(self.pos_admin).open_ui()
            self.start_pos_tour('test_payment_method_close_session', pos_config=self.urban_piper_config, login="pos_admin")

    def test_multi_branch_tax_setup(self):
        self.parent_company = self.company_data['company']
        self.child_company = self.env['res.company'].create({
            'name': 'Branch Company',
            'parent_id': self.parent_company.id,
            'chart_template': self.env.company.chart_template,
            'country_id': self.env.company.country_id.id,
        })
        bank_payment_method = self.bank_payment_method.copy()
        bank_payment_method.company_id = self.child_company.id
        self.tax_15 = self.env['account.tax'].create({
            'name': '15% VAT',
            'amount': 15,
            'amount_type': 'percent',
            'company_id': self.parent_company.id,
        })
        self.product_1 = self.env['product.template'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'taxes_id': [(4, self.tax_15.id)],
            'type': 'consu',
            'list_price': 100.0,
        })
        self.child_branch_pos_config = self.env['pos.config'].with_company(self.child_company).create({
            'name': 'Branch POS',
            'module_pos_urban_piper': True,
            'urbanpiper_delivery_provider_ids': [Command.set([self.env.ref('pos_urban_piper.pos_delivery_provider_justeat').id])],
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_journal_id': self.company_data['default_journal_sale'].id,
            'payment_method_ids': [(4, bank_payment_method.id)],
        })
        self.child_branch_pos_config.open_ui()
        with MockRequest(self.env):
            self.make_test_order({
                'product_id': self.product_1,
                'quantity': 2,
                'delivery_instruction': 'Leave at door',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat'),
                'delivery_identifier': "order1",
                'config_id': self.child_branch_pos_config,
            })
        order = self.env['pos.order'].search([('delivery_identifier', '=', 'order1')])
        order.config_id._make_order_payment(order)
        self.assertEqual(order.amount_difference, 0.0)
        self.assertEqual(order.amount_paid, 200.01)

        def _mock_make_api_request(self, endpoint, method='POST', data=None, timeout=10):
            return []

        with patch.object(UrbanPiperClient, "_make_api_request", _mock_make_api_request):
            self.child_branch_pos_config.order_status_update(order.id, 'Food Ready')
        self.assertEqual(self.tax_15.id, order.lines.tax_ids.id)

    def test_product_taxes(self):
        self.tax_15 = self.env['account.tax'].create({
            'name': '15% VAT',
            'amount': 15,
            'amount_type': 'percent',
        })
        self.product_1.taxes_id = [(4, self.tax_15.id)]
        packaging_product = self.env.ref('pos_urban_piper.product_packaging_charges', False)
        delivery_product = self.env.ref('pos_urban_piper.product_delivery_charges', False)
        packaging_product.taxes_id = [(6, 0, self.tax_15.ids)]
        self.discount_product.taxes_id = [(6, 0, self.tax_15.ids)]
        delivery_product.taxes_id = [(5, 0, 0)]
        self.urban_piper_config.open_ui()
        with MockRequest(self.env):
            self.make_test_order({
                'product_id': self.product_1,
                'quantity': 2,
                'delivery_instruction': 'Leave at door',
                'delivery_provider_id': self.env.ref('pos_urban_piper.pos_delivery_provider_justeat'),
                'delivery_identifier': "order1",
                'config_id': self.urban_piper_config,
                'has_tax': False,
                'packaging_charge': 10.0,
                'delivery_charge': 10.0,
                'discount_amount': 10.0
            })
        order = self.env['pos.order'].search([('delivery_identifier', '=', 'order1')])
        self.assertEqual(order.lines[0].tax_ids.id, self.tax_15.id)
        self.assertEqual(order.lines[1].tax_ids.id, self.tax_15.id)
        self.assertEqual(order.lines[2].tax_ids.id, False)
        self.assertEqual(order.lines[3].tax_ids.id, self.tax_15.id)

    def test_charges_sent_to_urbanpiper(self):
        up = UrbanPiperClient(self.urban_piper_config)
        delivery_charge_product = self.env.ref('pos_urban_piper.product_delivery_charges')
        delivery_charge_product.list_price = 10
        charges = up._prepare_charges_data()
        self.assertEqual(
            charges,
            [{'code': 'DC_F', 'title': 'Delivery Charges', 'active': True, 'structure': {'applicable_on': 'order.order_subtotal', 'value': 10.0}, 'item_ref_ids': ['all']}]
        )
