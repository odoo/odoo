# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import pairwise
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tests import Form, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestPricelist(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.datacard = cls.env['product.product'].create({'name': 'Office Lamp'})
        cls.usb_adapter = cls.env['product.product'].create({'name': 'Office Chair'})

        cls.sale_pricelist_id, cls.pricelist_eu = cls.env['product.pricelist'].create([{
            'name': 'Sale pricelist',
            'item_ids': [
                Command.create({
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_discount': 10,
                    'product_id': cls.usb_adapter.id,
                    'applied_on': '0_product_variant',
                }),
                Command.create({
                    'compute_price': 'formula',
                    'base': 'list_price',  # based on public price
                    'price_surcharge': -0.5,
                    'product_id': cls.datacard.id,
                    'applied_on': '0_product_variant',
                }),
                Command.create({
                    'compute_price': 'formula',
                    'base': 'standard_price',  # based on cost
                    'price_markup': 99.99,
                    'applied_on': '3_global',
                }),
            ],
        }, {
            'name': "EU Pricelist",
            'country_group_ids': cls.env.ref('base.europe').ids,
        }])

        # Enable pricelist feature
        cls.env.user.group_ids += cls.env.ref('product.group_product_pricelist')
        cls.uom_ton = cls.env.ref('uom.product_uom_ton')

    def test_10_discount(self):
        # Make sure the price using a pricelist is the same than without after
        # applying the computation manually

        self.assertEqual(
            self.pricelist._get_product_price(self.usb_adapter, 1.0)*0.9,
            self.sale_pricelist_id._get_product_price(self.usb_adapter, 1.0))

        self.assertEqual(
            self.pricelist._get_product_price(self.datacard, 1.0)-0.5,
            self.sale_pricelist_id._get_product_price(self.datacard, 1.0))

        self.assertAlmostEqual(
            self.sale_pricelist_id._get_product_price(self.usb_adapter, 1.0, uom=self.uom_unit)*12,
            self.sale_pricelist_id._get_product_price(self.usb_adapter, 1.0, uom=self.uom_dozen))

        # price_surcharge applies to product default UoM, here "Units", so surcharge will be multiplied
        self.assertAlmostEqual(
            self.sale_pricelist_id._get_product_price(self.datacard, 1.0, uom=self.uom_unit)*12,
            self.sale_pricelist_id._get_product_price(self.datacard, 1.0, uom=self.uom_dozen))

    def test_11_markup(self):
        """Ensure `price_markup` always equals negative `price_discount`."""
        # Check create values
        for item in self.sale_pricelist_id.item_ids:
            self.assertEqual(item.price_markup, -item.price_discount)

        # Overwrite create values, and check again
        self.sale_pricelist_id.item_ids[0].price_discount = 0
        self.sale_pricelist_id.item_ids[1].price_discount = -20.02
        self.sale_pricelist_id.item_ids[2].price_markup = -0.5
        for item in self.sale_pricelist_id.item_ids:
            self.assertEqual(item.price_markup, -item.price_discount)

    def test_20_pricelist_uom(self):
        # Verify that the pricelist rules are correctly using the product's default UoM
        # as reference, and return a result according to the target UoM (as specific in the context)

        tonne_price = 100

        # setup product stored in 'tonnes', with a discounted pricelist for qty > 3 tonnes
        spam = self.env['product.product'].create({
            'name': '1 tonne of spam',
            'uom_id': self.uom_ton.id,
            'list_price': tonne_price,
            'type': 'consu'
        })

        self.env['product.pricelist.item'].create({
            'pricelist_id': self.pricelist.id,
            'applied_on': '0_product_variant',
            'compute_price': 'formula',
            'base': 'list_price',  # based on public price
            'min_quantity': 3,  # min = 3 tonnes
            'price_surcharge': -10,  # -10 EUR / tonne
            'product_id': spam.id
        })

        def test_unit_price(qty, uom_id, expected_unit_price):
            uom = self.env['uom.uom'].browse(uom_id)
            unit_price = self.pricelist._get_product_price(spam, qty, uom=uom)
            self.assertAlmostEqual(unit_price, expected_unit_price, msg='Computed unit price is wrong')

        # Test prices - they are *per unit*, the quantity is only here to match the pricelist rules!
        test_unit_price(2, self.uom_kgm.id, tonne_price / 1000.0)
        test_unit_price(2000, self.uom_kgm.id, tonne_price / 1000.0)
        test_unit_price(3500, self.uom_kgm.id, (tonne_price - 10) / 1000.0)
        test_unit_price(2, self.uom_ton.id, tonne_price)
        test_unit_price(3, self.uom_ton.id, tonne_price - 10)

    def test_30_pricelists_order(self):
        # Verify the order of pricelists after creation

        ProductPricelist = self.env['product.pricelist']
        res_partner = self.env['res.partner'].create({'name': 'Ready Corner'})

        ProductPricelist.search([]).active = False

        pl_first = ProductPricelist.create({'name': 'First Pricelist'})
        res_partner.invalidate_recordset(['property_product_pricelist'])

        self.assertEqual(res_partner.property_product_pricelist, pl_first)

        ProductPricelist.create({'name': 'Second Pricelist'})
        res_partner.invalidate_recordset(['property_product_pricelist'])

        self.assertEqual(res_partner.property_product_pricelist, pl_first)

    def test_40_specific_property_product_pricelist(self):
        """Ensure that that ``specific_property_product_pricelist`` value only gets set
        when changing ``property_product_pricelist`` to a non-default value for the partner.
        """
        pricelist_1, pricelist_2 = self.pricelist, self.sale_pricelist_id
        self.env['product.pricelist'].search([
            ('id', 'not in', [pricelist_1.id, pricelist_2.id, self.pricelist_eu.id]),
        ]).active = False

        # Set country to BE -> property defaults to EU pricelist
        with Form(self.partner) as partner_form:
            partner_form.country_id = self.env.ref('base.be')
        self.assertEqual(self.partner.property_product_pricelist, self.pricelist_eu)
        self.assertFalse(self.partner.specific_property_product_pricelist)

        # Set country to KI -> property defaults to highest sequence pricelist
        with Form(self.partner) as partner_form:
            partner_form.country_id = self.env.ref('base.ki')
        self.assertEqual(self.partner.property_product_pricelist, pricelist_1)
        self.assertFalse(self.partner.specific_property_product_pricelist)

        # Setting non-default pricelist as property should update specific property
        with Form(self.partner) as partner_form:
            partner_form.property_product_pricelist = pricelist_2
        self.assertEqual(self.partner.property_product_pricelist, pricelist_2)
        self.assertEqual(self.partner.specific_property_product_pricelist, pricelist_2)

        # Changing partner country shouldn't update (specific) pricelist property
        with Form(self.partner) as partner_form:
            partner_form.country_id = self.env.ref('base.be')
        self.assertEqual(self.partner.property_product_pricelist, pricelist_2)
        self.assertEqual(self.partner.specific_property_product_pricelist, pricelist_2)

    def test_45_property_product_pricelist_config_parameter(self):
        """Check that the ``ir.config_parameter`` gets utilized as fallback to both
        ``property_product_pricelist`` & ``specific_property_product_pricelist``.
        """
        pricelist_1, pricelist_2 = self.pricelist, self.sale_pricelist_id
        self.env['product.pricelist'].search([
            ('id', 'not in', [pricelist_1.id, pricelist_2.id]),
        ]).active = False
        self.assertEqual(self.partner.property_product_pricelist, pricelist_1)

        self.partner.invalidate_recordset(['property_product_pricelist'])
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('res.partner.property_product_pricelist', pricelist_2.id)
        with patch.object(
            self.pricelist.__class__,
            '_get_partner_pricelist_multi_search_domain_hook',
            return_value=Domain.FALSE,  # ensures pricelist falls back on ICP
        ):
            with Form(self.partner) as partner_form:
                self.assertEqual(partner_form.property_product_pricelist, pricelist_2)
                partner_form.property_product_pricelist = pricelist_1
            self.assertEqual(self.partner.property_product_pricelist, pricelist_1)
            self.assertEqual(self.partner.specific_property_product_pricelist, pricelist_1)

    def test_pricelists_multi_comp_checks(self):
        first_company = self.env.company
        second_company = self.env['res.company'].create({'name': 'Test Company'})

        shared_pricelist = self.env['product.pricelist'].create({
            'name': 'Test Multi-comp pricelist',
            'company_id': False,
        })
        second_pricelist = self.env['product.pricelist'].create({
            'name': f'Second test pricelist{first_company.name}',
        })

        self.assertEqual(self.pricelist.company_id, first_company)
        self.assertFalse(shared_pricelist.company_id)
        self.assertEqual(second_pricelist.company_id, first_company)

        with self.assertRaises(UserError):
            shared_pricelist.item_ids = [
                Command.create({
                    'compute_price': 'formula',
                    'base': 'pricelist',
                    'base_pricelist_id': self.pricelist.id,
                })
            ]

        self.pricelist.item_ids = [
            Command.create({
                'compute_price': 'formula',
                'base': 'pricelist',
                'base_pricelist_id': shared_pricelist.id,
            }),
            Command.create({
                'compute_price': 'formula',
                'base': 'pricelist',
                'base_pricelist_id': second_pricelist.id,
            })
        ]

        with self.assertRaises(UserError):
            # Should raise because the pricelist would have a rule based on a pricelist
            # from another company
            self.pricelist.company_id = second_company

    def test_pricelists_res_partner_form(self):
        pricelist_europe = self.pricelist_eu
        default_pricelist = self.env['product.pricelist'].search([('name', 'ilike', ' ')], limit=1)

        with Form(self.env['res.partner']) as partner_form:
            partner_form.name = "test"
            self.assertEqual(partner_form.property_product_pricelist, default_pricelist)

            partner_form.country_id = self.env.ref('base.be')
            self.assertEqual(partner_form.property_product_pricelist, pricelist_europe)

            partner_form.property_product_pricelist = self.sale_pricelist_id
            self.assertEqual(partner_form.property_product_pricelist, self.sale_pricelist_id)

            partner = partner_form.save()

        with Form(partner) as partner_form:
            self.assertEqual(partner_form.property_product_pricelist, self.sale_pricelist_id)

    def test_pricelist_change_to_formula_and_back(self):
        pricelist_2 = self.env['product.pricelist'].create({
            'name': 'Sale pricelist 2',
            'item_ids': [
                Command.create({
                    'compute_price': 'percentage',
                    'percent_price': 20,
                    'base': 'pricelist',
                    'base_pricelist_id': self.sale_pricelist_id.id,
                    'applied_on': '3_global',
                }),
            ],
        })
        with Form(pricelist_2.item_ids) as item_form:
            item_form.compute_price = 'formula'
            item_form.compute_price = 'percentage'
            item_form.percent_price = 20
        self.assertFalse(pricelist_2.item_ids.base_pricelist_id.id)

    def test_sync_parent_pricelist(self):
        """Check that adding a parent to a partner updates the partner's pricelist."""
        self.partner.update({
            'parent_id': False,
            'specific_property_product_pricelist': self.sale_pricelist_id.id,
        })
        self.assertEqual(self.partner.property_product_pricelist, self.sale_pricelist_id)

        company_2 = self.env.company.create({'name': "Company Two"})
        company_1_b2b_pl, company_2_b2b_pl = self.sale_pricelist_id.create([{
            'name': f"B2B ({company.name})",
            'company_id': company.id,
        } for company in self.env.company + company_2])
        parent = self.partner.create({
            'name': f"{self.partner.name}'s Company",
            'is_company': True,
            'specific_property_product_pricelist': company_1_b2b_pl.id,
        })
        parent.with_company(company_2).specific_property_product_pricelist = company_2_b2b_pl

        self.partner.parent_id = parent
        self.assertEqual(
            self.partner.specific_property_product_pricelist,
            company_1_b2b_pl,
            "Assigning a parent with a specific pricelist should sync the parent's pricelist",
        )
        self.assertEqual(
            self.partner.with_company(company_2).specific_property_product_pricelist,
            company_2_b2b_pl,
            "Company-specific pricelists should get synced on parent assignment",
        )

        parent.specific_property_product_pricelist = self.sale_pricelist_id
        self.assertEqual(
            self.partner.specific_property_product_pricelist,
            self.sale_pricelist_id,
            "Setting a specific parent pricelist should update the partner's pricelist",
        )
        self.assertEqual(
            self.partner.with_company(company_2).specific_property_product_pricelist,
            company_2_b2b_pl,
            "Assigning pricelists in one company shouldn't impact pricelists in other companies",
        )

    def test_prevent_pricelist_recursion(self):
        """Ensure recursive pricelist rules raise an error on creation."""
        def create_item_vals(pl_from, pl_to):
            return {
                'pricelist_id': pl_from.id,
                'compute_price': 'formula',
                'base': 'pricelist',
                'base_pricelist_id': pl_to.id,
                'applied_on': '3_global',
            }
        Pricelist = self.env['product.pricelist']
        pl_a, pl_b, pl_c, pl_d = pricelists = Pricelist.create([{
            'name': f"Pricelist {c}",
        } for c in 'ABCD'])

        # A -> B -> C -> D
        Pricelist.item_ids.create([
            create_item_vals(pl_from, pl_to)
            for (pl_from, pl_to) in pairwise(pricelists)
        ])

        with self.assertRaises(ValidationError):
            # A -> B -> C -> D -> D -> _ (recurs)
            Pricelist.item_ids.create(create_item_vals(pl_d, pl_d))
        with self.assertRaises(ValidationError):
            # A -> B -> C -> D -> A -> _ (recurs)
            Pricelist.item_ids.create(create_item_vals(pl_d, pl_a))
        with self.assertRaises(ValidationError):
            # A -> B -> C -> [B -> _, D] (recurs)
            Pricelist.item_ids.create(create_item_vals(pl_c, pl_b))

        # A -> B, C -> D
        pl_b.item_ids.unlink()
        # C -> D -> A -> B
        Pricelist.item_ids.create(create_item_vals(pl_d, pl_a))
        # C -> [B, D -> A -> B]
        Pricelist.item_ids.create(create_item_vals(pl_c, pl_b))

        with self.assertRaises(ValidationError):
            # C -> [B, D -> A -> [B, C -> _]] (recurs)
            Pricelist.item_ids.create(create_item_vals(pl_a, pl_c))
        with self.assertRaises(ValidationError):
            # C -> [B -> D -> A -> B -> _, D -> _] (recurs)
            Pricelist.item_ids.create(create_item_vals(pl_b, pl_d))

    def test_pricelist_rule_linked_to_product_variant(self):
        """Verify that pricelist rules assigned to a variant remain linked after write."""
        self.product_sofa_red.pricelist_rule_ids = [
            Command.create({
                'applied_on': '0_product_variant',
                'product_id': self.product_sofa_red.id,
                'compute_price': 'fixed',
                'fixed_price': 99.9,
                'pricelist_id': self.pricelist.id,
            }),
            Command.create({
                'applied_on': '0_product_variant',
                'product_id': self.product_sofa_red.id,
                'compute_price': 'fixed',
                'fixed_price': 89.9,
                'pricelist_id': self.pricelist.id,
            }),
        ]
        self.assertEqual(len(self.product_sofa_red.pricelist_rule_ids), 2)
        first_rule, second_rule = self.product_sofa_red.pricelist_rule_ids
        self.product_sofa_red.pricelist_rule_ids = [
            Command.update(first_rule.id, {'fixed_price': 79.9}),
            Command.unlink(second_rule.id),
        ]
        self.assertEqual(len(self.product_sofa_red.pricelist_rule_ids), 1)
        self.assertEqual(self.pricelist.item_ids.fixed_price, 79.9)
        self.assertIn(self.product_sofa_red, self.pricelist.item_ids.product_id)

        # Update of template-based rules through variant form
        self.product_template_sofa.pricelist_rule_ids = [
            # Template-based rule (can be edited through the variants)
            Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': self.product_template_sofa.id,
                'pricelist_id': self.pricelist.id,
            }),
            # Rule on another variant than the one being edited. It cannot be edited through the
            # current variant and therefore shouldn't change when another variant rules are edited.
            Command.create({
                'applied_on': '0_product_variant',
                'product_id': self.product_sofa_blue.id,
                'compute_price': 'fixed',
                'fixed_price': 89.9,
                'pricelist_id': self.pricelist.id,
            })
        ]
        self.assertEqual(len(self.product_template_sofa.pricelist_rule_ids), 3)
        template_rule = self.product_template_sofa.pricelist_rule_ids.filtered(
            lambda item: not item.product_id
        )
        self.assertEqual(len(self.product_sofa_red.pricelist_rule_ids), 2)
        self.product_sofa_red.pricelist_rule_ids = [
            Command.update(template_rule.id, {'fixed_price': 133}),
        ]
        self.assertEqual(template_rule.fixed_price, 133)

        self.product_sofa_red.pricelist_rule_ids = [
            Command.unlink(template_rule.id),
        ]
        self.assertFalse(template_rule.exists())

        self.assertTrue(self.product_sofa_blue.pricelist_rule_ids)
        self.assertEqual(len(self.product_template_sofa.pricelist_rule_ids), 2)

    def test_pricelist_applied_on_product_variant(self):
        # product template with variants
        sofa_1 = self.product_template_sofa.product_variant_ids[0]
        # create pricelist with rule on template
        pricelist = self.env["product.pricelist"].create(
            {
                "name": "Pricelist for Acoustic Bloc Screens",
                "item_ids": [
                    Command.create(
                        {
                            "compute_price": "fixed",
                            "fixed_price": 123,
                            "base": "list_price",
                            "applied_on": "1_product",
                            "product_tmpl_id": self.product_template_sofa.id,
                        }
                    ),
                ],
            }
        )
        # open rule form and change rule to apply on variant instead of template
        with Form(pricelist.item_ids) as item_form:
            item_form.product_id = sofa_1
        # check that `applied_on` changed to variant
        self.assertEqual(pricelist.item_ids.applied_on, "0_product_variant")
        # re-edit rule to apply on template again by clearing `product_id`
        with Form(pricelist.item_ids) as item_form:
            item_form.product_id = self.env["product.product"]
        # check that `applied_on` changed to template
        self.assertEqual(pricelist.item_ids.applied_on, "1_product")
        # check that product_id is cleared
        self.assertFalse(pricelist.item_ids.product_id)
