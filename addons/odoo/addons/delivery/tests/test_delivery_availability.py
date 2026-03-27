# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestDeliveryAvailability(DeliveryCommon, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.must_have_tag = cls.env['product.tag'].create({
            'name': 'Must Have',
        })
        cls.exclude_tag = cls.env['product.tag'].create({
            'name': 'Exclude',
        })

        cls.non_restricted_carrier = cls._prepare_carrier(cls.carrier.product_id)
        cls.product2 = cls._prepare_carrier_product(name='Test Product 2')

    def test_00_order_with_heavy_product_simple(self):
        self.carrier.write({
            'max_weight': 10.0,
        })

        self.product.write({
            'weight': 11.0,
        })

        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Product weight exceeds carrier's max weight")

    def test_01_order_with_heavy_product_different_uom(self):
        self.carrier.write({
            'max_weight': 10.0,
        })

        self.product.write({
            'weight': 1.0,
        })

        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_dozen.id,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Order lines should be converted to the default UoM before checking weight")

    def test_02_order_with_big_product_simple(self):
        self.carrier.write({
            'max_volume': 10.0,
        })

        self.product.write({
            'volume': 11.0,
        })

        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Product volume exceeds carrier's max volume")

    def test_03_order_with_big_product_different_uom(self):
        self.carrier.write({
            'max_volume': 10.0,
        })

        self.product.write({
            'volume': 1.0,
        })

        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'product_uom': self.uom_dozen.id,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Order lines should be converted to the default UoM before checking volume")

    def test_04_check_must_have_tag(self):
        self.carrier.must_have_tag_ids = [
            Command.link(self.must_have_tag.id),
            Command.link(self.must_have_tag.copy({'name': "Alt Must Have"}).id),
        ]

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier must have tag is not set on any product in the order")

        self.product.write({
            'product_tag_ids': [self.must_have_tag.id],
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertTrue(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier must have tag is set on one product in the order")

    def test_05_check_excluded_tag(self):
        self.carrier.write({
            'excluded_tag_ids': [self.exclude_tag.id],
        })

        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertTrue(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier excluded tag is not set on any product in the order")

        self.product.write({
            'product_tag_ids': [self.exclude_tag.id],
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier excluded tag is set on one product in the order")

    def test_06_check_tags_complex(self):
        self.carrier.write({
            'must_have_tag_ids': [self.must_have_tag.id],
            'excluded_tag_ids': [self.exclude_tag.id],
        })

        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'product_id': self.product2.id,
                    'product_uom_qty': 1,
                })
            ],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier must have tag is not set on any product in the order")

        self.product.write({
            'product_tag_ids': [self.must_have_tag.id],
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertTrue(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier must have tag is set on one product in the order")

        self.product.write({
            'product_tag_ids': [self.exclude_tag.id, self.must_have_tag.id],
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier excluded tag is set on one product in the order")

        self.product.write({
            'product_tag_ids': [self.must_have_tag.id],
        })
        self.product2.write({
            'product_tag_ids': [self.exclude_tag.id],
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_order.id,
            'default_carrier_id': self.non_restricted_carrier.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        self.assertFalse(self.carrier.id in choose_delivery_carrier.available_carrier_ids.ids, "Carrier excluded tag is set on one product in the order")
