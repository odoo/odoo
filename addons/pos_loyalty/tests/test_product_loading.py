# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import timedelta
from math import floor

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPOSLoyaltyProductLoading(TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    def test_loyalty_product_loading(self):
        """ Test that loyalty products are loaded correctly in the PoS session. """
        new_product = self.env['product.product'].create({
            'name': 'New Product',
            'is_storable': True,
            'list_price': 1,
            'available_in_pos': True,
            'taxes_id': False,
        })

        self.env['loyalty.program'].search([]).write({
            'active': False,
        })

        self.env['loyalty.program'].create({
            'name': 'Program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': new_product.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })

        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 1)

        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        data = current_session.load_data({
            'models': ['pos.config', 'product.template', 'product.product'],
            'only_records': True,
        })

        product = next((n for n in data['product.product'] if n['id'] == new_product.id and n['_is_pos_special_product']), None)
        self.assertIsNone(product,
                        "Loyalty product should not be _is_pos_special_product when program is inactive.")

        data = current_session.load_data({
            'models': ['pos.config', 'product.template', 'product.product'],
            'only_records': True,
        })

        product = next((n for n in data['product.template'] if n['id'] == new_product.product_tmpl_id.id), None)
        self.assertIsNotNone(product,
                        "Loyalty product should be loaded in the PoS session when program is active.")

        self.assertIsNone(next((n for n in data['product.product'] if n['id'] == new_product.id and n['_is_pos_special_product']), None),
                        "Loyalty product should not be _is_pos_special_product since it is loaded.")

        # Make the product not available in the PoS
        new_product.write({'available_in_pos': False})

        data = current_session.load_data({
            'models': ['pos.config', 'product.template', 'product.product'],
            'only_records': True,
        })

        self.assertIn(new_product.product_tmpl_id.id, [product['id'] for product in data['product.template']],
                        "Loyalty product should be loaded in the PoS session when it is used in a program, even if not available in the PoS.")

        self.assertIsNotNone(next((n for n in data['product.product'] if n['id'] == new_product.id and n['_is_pos_special_product']), None),
                        "Loyalty product should be in _pos_special_products_ids since it is loaded but not available in the PoS.")

    def test_product_loading_without_gift_card(self):
        """
        Test that products are loaded correctly in the PoS session of company
        if special loyalty products are not visible to them
        """
        gift_card = self.env.ref('loyalty.gift_card_product_50').sudo()
        gift_card.company_id = self.env.company

        company_b_data = self.setup_other_company(name='Company B')
        company_b = company_b_data['company']
        payment_method = self.env['pos.payment.method'].create({
            'name': 'Cash',
            'type': 'cash',
            'receivable_account_id': company_b_data['default_account_receivable'].id,
            'journal_id': company_b_data['default_journal_cash'].id,
            'company_id': company_b.id,
        })
        pos_config = self.env['pos.config'].create({
            'name': 'new pos',
            'company_id': company_b.id,
            'journal_id': company_b_data['default_journal_sale'].id,
            'payment_method_ids': [Command.set([payment_method.id])],
        })
        pos_config.open_ui()
        current_session = pos_config.current_session_id
        data = current_session.with_company(company_b).load_data({'models': ['pos.config', 'product.template'], 'only_records': True})
        self.assertTrue(len(data['product.template']) > 0)
        self.assertNotIn(gift_card.product_tmpl_id.id, [product['id'] for product in data['product.template']],
                        "Product should be loaded in the PoS session, even if Gift card is not available in the PoS.")

    def test_incremental_load_rule_valid_products_of_changed_products(self):
        """Products entering or leaving an unchanged rule after the last sync:
        the rule has to be resent with its up-to-date valid_product_ids."""
        self.env['loyalty.program'].search([]).write({'active': False})
        program = self.env['loyalty.program'].create({
            'name': 'Loyalty',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 1,
                'product_domain': '[("available_in_pos", "=", True)]',
            })],
        })
        rule = program.rule_ids
        old_product = self.env['product.product'].create({
            'name': 'Old Socks',
            'list_price': 20,
            'available_in_pos': True,
        })
        self.main_pos_config.open_ui()
        session = self.main_pos_config.current_session_id

        # The client cached the rule and the products a while ago
        self.env.flush_all()
        old_date = fields.Datetime.now() - timedelta(days=30)
        self.env.cr.execute("UPDATE loyalty_rule SET write_date = %s", (old_date,))
        self.env.cr.execute("UPDATE product_product SET write_date = %s", (old_date,))
        self.env.cr.execute("UPDATE product_template SET write_date = %s", (old_date,))
        self.env.invalidate_all()
        cache = {
            model: {str(record.id): floor(record.write_date.timestamp()) for record in self.env[model].search([])}
            for model in ('loyalty.rule', 'product.product', 'product.template')
        }

        def load_rules_from_cache():
            # non-stored compute: a new request would not have it cached
            rule.invalidate_recordset(['valid_product_ids'])
            data = session.load_data({'models': ['loyalty.rule'], 'records': cache, 'only_records': True})
            return {r['id']: r for r in data['loyalty.rule']}

        self.assertNotIn(rule.id, load_rules_from_cache(), "unchanged rule is not resent when no product changed")

        old_product.available_in_pos = False
        rules = load_rules_from_cache()
        self.assertIn(rule.id, rules, "rule must be resent when a product left it since the last sync")
        self.assertNotIn(old_product.id, rules[rule.id]['valid_product_ids'])

        new_product = self.env['product.product'].create({
            'name': 'New Socks',
            'list_price': 20,
            'available_in_pos': True,
        })
        rules = load_rules_from_cache()
        self.assertIn(new_product.id, rules[rule.id]['valid_product_ids'])
