# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.fields import Command


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_free_delivery_when_exceed_threshold(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        # Avoid Shipping/Billing address page
        self.env.ref('base.partner_admin').write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })

        self.env['product.product'].create({
            'name': 'Office Chair Black TEST',
            'list_price': 12.50,
        })
        self.env.ref("delivery.free_delivery_carrier").write({
            'name': 'Delivery Now Free Over 10',
            'fixed_price': 2,
            'free_over': True,
            'amount': 10,
        })
        self.product_delivery_poste = self.env['product.product'].create({
            'name': 'The Poste',
            'type': 'service',
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 20.0,
        })
        self.carrier = self.env['delivery.carrier'].create({
            'name': 'The Poste',
            'sequence': 9999, # ensure last to load price async
            'fixed_price': 20.0,
            'delivery_type': 'base_on_rule',
            'product_id': self.product_delivery_poste.id,
            'website_published': True,
            'price_rule_ids': [
                Command.create({
                    'max_value': 5,
                    'list_base_price': 20,
                }),
                Command.create({
                    'operator': '>=',
                    'max_value': 5,
                    'list_base_price': 50,
                }),
                Command.create({
                    'operator': '>=',
                    'max_value': 300,
                    'variable': 'price',
                    'list_base_price': 0,
                }),
            ]
        })

        self.start_tour("/", 'check_free_delivery', login="admin")

    def test_line_price_updated_on_delivery_address_change(self):
        self.env["website"].get_current_website().show_line_subtotals_tax_selection = "tax_included"
        address = {
            "city": "Brussels", "zip": "1000", "phone": "+32 555 55 55 55",
            "email": "admin@yourcompany.example.com",
        }
        admin_partner = self.env.ref("base.partner_admin")
        admin_partner.write({
            **address, "street": "Domestic Street", "country_id": self.env.ref("base.be").id,
        })
        self.env["res.partner"].create({
            **address,
            "name": "Foreign Address",
            "type": "delivery",
            "parent_id": admin_partner.id,
            "street": "Foreign Street",
            "country_id": self.env.ref("base.fr").id,
        })
        fpos = self.env["account.fiscal.position"].create({
            "name": "FR",
            "auto_apply": True,
            "country_id": self.env.ref("base.fr").id,
        })
        tax_21, tax_20 = self.env["account.tax"].create([
            {"name": "Tax 21%", "amount": 21},
            {"name": "Tax 20%", "amount": 20, "fiscal_position_ids": fpos.ids},
        ])
        tax_20.original_tax_ids = tax_21
        self.env["product.product"].create({
            "name": "Fiscal Product",
            "list_price": 100,
            "taxes_id": tax_21.ids,
            "is_published": True,
        })
        self.env["delivery.carrier"].create({
            "name": "Free Delivery",
            "fixed_price": 0,
            "product_id": self.env["product.product"].create({
                "name": "Free Delivery", "type": "service", "sale_ok": False,
            }).id,
            "is_published": True,
        })
        self.start_tour("/", "website_sale_line_price_after_delivery_address_change", login="admin")
