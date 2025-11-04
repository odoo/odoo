# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestSuggestedProducts(WebsiteSaleCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create product categories
        cls.category_desks = cls.env['product.public.category'].create({'name': 'Desks'})
        cls.category_chairs = cls.env['product.public.category'].create({'name': 'Chairs'})

        # Create product templates
        cls.template_desk = cls.env['product.template'].create({
            'name': 'Desk',
            'list_price': 100,
            'public_categ_ids': [Command.link(cls.category_desks.id)],
            'is_published': True,
        })
        cls.template_chair = cls.env['product.template'].create({
            'name': 'Chair',
            'list_price': 50,
            'public_categ_ids': [Command.link(cls.category_chairs.id)],
            'is_published': True,
        })
        cls.template_combo_desk_chair = cls.env['product.template'].create({
            'name': 'Desk + Chair',
            'public_categ_ids':
                [Command.link(cls.category_desks.id), Command.link(cls.category_chairs.id)],
            'is_published': True,
        })
        # Create sale orders
        cls.so_1 = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({'product_id': cls.template_desk.product_variant_id.id}),
                Command.create({'product_id': cls.template_chair.product_variant_id.id}),
            ],
            'state': 'sale',
        })
        cls.so_2 = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({'product_id': cls.template_desk.product_variant_id.id}),
                Command.create({'product_id': cls.template_chair.product_variant_id.id}),
            ],
            'state': 'sale',
        })

    def test_01_activate_suggested_products_settings_triggers_cron(self):
        """Activating the website settings automatically triggers the cron
        updating the optional and alternative products."""
        suggested_products_cron = self.env.ref('website_sale.ir_cron_update_suggested_products')
        with self.capture_triggers(
                'website_sale.ir_cron_update_suggested_products'
        ) as captured_triggers:
            # Enable the suggested products feature
            self.env['res.config.settings'].create({'group_suggested_products': True}).set_values()
        self.assertTrue(suggested_products_cron.active)
        # Assert that a trigger was created
        self.assertEqual(len(captured_triggers.records), 1)

    def test_02_update_suggested_products_sets_alternative_products(self):
        """_update_suggested_products fills alternative products based on shared categories."""
        # Clear any existing alternatives
        tested_products = self.template_desk | self.template_chair | self.template_combo_desk_chair
        tested_products.alternative_product_ids = False
        # Update suggested products on tested_products
        tested_products._update_suggested_products()
        self.assertEqual(self.template_desk.alternative_product_ids, self.template_combo_desk_chair)
        self.assertEqual(self.template_chair.alternative_product_ids, self.template_combo_desk_chair)
        chair_and_desk = self.template_chair | self.template_desk
        self.assertEqual(self.template_combo_desk_chair.alternative_product_ids, chair_and_desk)

    def test_03_update_suggested_products_sets_optional_products(self):
        """Test that _update_suggested_products fills optional products based on sales history."""
        # Clear any existing optional products
        self.template_desk.optional_product_ids = False
        # Update suggested products for template_desk
        self.template_desk._update_suggested_products()
        self.assertEqual(self.template_desk.optional_product_ids, self.template_chair)

    def test_04_cron_write_preserves_automation(self):
        """Test that writing from cron context doesn't disable the automation flags."""
        self.template_desk.suggest_alternative_products = True
        self.template_desk.suggest_optional_products = True

        # Write from cron context
        self.template_desk.with_context(cron_id=1).write({
            'alternative_product_ids': [Command.link(self.template_chair.id)],
            'optional_product_ids': [Command.link(self.template_chair.id)],
        })
        self.assertTrue(self.template_desk.suggest_alternative_products)
        self.assertTrue(self.template_desk.suggest_optional_products)

    def test_05_manual_write_disables_automation(self):
        """Test that manually writing disables the automation flags."""
        # Ensure the automation is set for template_desk
        self.template_desk.suggest_alternative_products = True
        self.template_desk.suggest_optional_products = True
        # Manually set alternative and optional products
        self.template_desk.write({
            'alternative_product_ids': [Command.link(self.template_chair.id)],
            'optional_product_ids': [Command.link(self.template_chair.id)],
        })
        self.assertFalse(self.template_desk.suggest_alternative_products)
        self.assertFalse(self.template_desk.suggest_optional_products)

    def test_06_action_reenables_automation(self):
        """Test that calling _update_suggested_products from the action re-enables automation."""
        self.template_desk.suggest_alternative_products = False
        self.template_desk.suggest_optional_products = False
        # Call from action (without cron_id context)
        self.template_desk._update_suggested_products()
        self.assertTrue(self.template_desk.suggest_alternative_products)
        self.assertTrue(self.template_desk.suggest_optional_products)

    def test_07_cron_only_updates_outdated_products(self):
        """Test that cron only updates products not updated within the last 12 hours."""
        now = fields.Datetime.now()
        recent_date = now - relativedelta(hours=6)
        old_date = now - relativedelta(hours=13)
        self.template_desk.suggested_products_last_update = recent_date
        self.template_chair.suggested_products_last_update = old_date
        products = self.template_desk | self.template_chair
        with patch.object(fields.Datetime, 'now', return_value=now):
            with self.enter_registry_test_mode(), self.env.registry.cursor() as cr:
                env = self.env(context={'cron_id': 1}, cr=cr)
                products.with_env(env)._update_suggested_products()
        # template_desk should not be updated (recently updated)
        self.assertEqual(self.template_desk.suggested_products_last_update, recent_date)
        # template_chair should be updated
        self.assertEqual(self.template_chair.suggested_products_last_update, now)
