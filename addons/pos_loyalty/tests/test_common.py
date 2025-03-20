from odoo import Command
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


class TestPoSLoyaltyDataHttpCommon(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # Ensure user permissions
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_user').id),
            ]
        })

        self.product_quality_article.write({'list_price': 50})
        self.product_quality_item.write({'list_price': 50})
        self.product_quality_thing.write({'list_price': 50})
        self.product_awesome_article.write({'list_price': 100})
        self.product_awesome_item.write({'list_price': 100})
        self.product_awesome_thing.write({
            'list_price': 100,
            'taxes_id': [(4, self.tax_10_include.id)]
        })

        self.setup_test_program(self)
        self.setup_test_coupon(self)
        self.edit_test_pos_config(self)

    def create_programs(self, details):
        """
        Create loyalty programs based on the details given.
        :param details: list of tuple ('name': str, 'program_type': 'gift_card' or 'ewallet')
        """
        LoyaltyProgram = self.env['loyalty.program']
        programs = {} # map: name -> program
        for (name, program_type) in details:
            program_id = LoyaltyProgram.create_from_template(program_type)['res_id']
            program = LoyaltyProgram.browse(program_id)
            program.write({'name': name})
            programs[name] = program
        return programs

    def edit_test_pos_config(self):
        # Set the programs to the pos config.
        # Remove fiscal position and pricelist.
        self.pos_config.write({
            'tax_regime_selection': False,
            'use_pricelist': False,
        })

    def setup_test_coupon(self):
        self.env["loyalty.generate.wizard"].with_context(
            {"active_id": self.coupon_program.id}
        ).create({"coupon_qty": 4, 'points_granted': 4.5}).generate_coupons()
        self.coupon1, self.coupon2, self.coupon3, self.coupon4 = self.coupon_program.coupon_ids
        self.coupon1.write({"code": "1234"})
        self.coupon2.write({"code": "5678"})
        self.coupon3.write({"code": "1357"})
        self.coupon4.write({"code": "2468"})

    def disable_test_program(self):
        self.code_promo_program.write({'active': False})
        self.auto_promo_program_current.write({'active': False})
        self.auto_promo_program_next.write({'active': False})
        self.coupon_program.write({'active': False})

    def setup_test_program(self):
        self.env['loyalty.program'].search([]).write({'active': False})

        # code promo program -> discount on specific products
        self.code_promo_program = self.env['loyalty.program'].create({
            'name': 'Promo Code Program - Discount on Specific Products',
            'program_type': 'promotion',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'promocode',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_ids': [
                    (4, self.product_awesome_article.product_variant_ids[0].id),
                    (4, self.product_awesome_item.product_variant_ids[0].id),
                    (4, self.product_awesome_thing.product_variant_ids[0].id),
                ],
            })],
        })

        # auto promo program on current order
        self.auto_promo_program_current = self.env['loyalty.program'].create({
            'name': 'Auto Promo Program - Cheapest Product',
            'program_type': 'promotion',
            'pos_config_ids': [(4, self.pos_config.id)],
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 90,
                'discount_mode': 'percent',
                'discount_applicability': 'cheapest',
            })]
        })

        # auto promo program on next order
        self.auto_promo_program_next = self.env['loyalty.program'].create({
            'name': 'Auto Promo Program - Global Discount',
            'program_type': 'promotion',
            'pos_config_ids': [(4, self.pos_config.id)],
            'trigger': 'auto',
            'applies_on': 'future',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })

        # coupon program -> free product
        self.coupon_program = self.env['loyalty.program'].create({
            'name': 'Coupon Program - Buy 3 Take 2 Free Product',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': self.product_awesome_article.product_variant_ids.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 3,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_awesome_article.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 1.5,
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
