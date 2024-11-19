# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.uom.tests.common import UomCommon


class ProductCommon(UomCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_product_pricelist = cls.quick_ref('product.group_product_pricelist')
        cls.product_category = cls.env['product.category'].create({
            'name': 'Test Category',
        })
        cls.product, cls.service_product = cls.env['product.product'].create([{
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 20.0,
            'categ_id': cls.product_category.id,
        }, {
            'name': 'Test Service Product',
            'type': 'service',
            'list_price': 50.0,
            'categ_id': cls.product_category.id,
        }])
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        # Archive all existing pricelists
        cls.env['product.pricelist'].search([
            ('id', '!=', cls.pricelist.id),
        ]).action_archive()

    @classmethod
    def _enable_product_variant(cls):
        """ Required for `product_id` to be visible in the view """
        cls.user.groups_id += cls.env.ref('product.group_product_variant')

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('base.group_system')

    @classmethod
    def _enable_pricelists(cls):
        cls.env.user.groups_id += cls.group_product_pricelist

    @classmethod
    def _archive_other_pricelists(cls):
        cls.env['product.pricelist'].search([
            ('id', '!=', cls.pricelist.id),
        ]).sudo().action_archive()

    @classmethod
    def _create_pricelist(cls, **create_vals):
        return cls.env['product.pricelist'].create({
            'name': "Test Pricelist",
            **create_vals,
        })

    @classmethod
    def _create_product(cls, **create_vals):
        return cls.env['product.product'].create({
            'name': "Test Product",
            'type': 'consu',
            'list_price': 100.0,
            'standard_price': 50.0,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'categ_id': cls.product_category.id,
            **create_vals,
        })


class ProductAttributesCommon(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.size_attribute = cls.env['product.attribute'].create({
            'name': 'Size',
            'value_ids': [
                Command.create({'name': 'S'}),
                Command.create({'name': 'M'}),
                Command.create({'name': 'L'}),
            ]
        })
        (
            cls.size_attribute_s,
            cls.size_attribute_m,
            cls.size_attribute_l,
        ) = cls.size_attribute.value_ids

        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({'name': 'red', 'sequence': 1}),
                Command.create({'name': 'blue', 'sequence': 2}),
                Command.create({'name': 'green', 'sequence': 3}),
            ],
        })
        (
            cls.color_attribute_red,
            cls.color_attribute_blue,
            cls.color_attribute_green,
        ) = cls.color_attribute.value_ids

        cls.no_variant_attribute = cls.env['product.attribute'].create({
            'name': 'No variant',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'extra'}),
                Command.create({'name': 'second'}),
            ]
        })
        (
            cls.no_variant_attribute_extra,
            cls.no_variant_attribute_second,
        ) = cls.no_variant_attribute.value_ids

        cls.dynamic_attribute = cls.env['product.attribute'].create({
            'name': 'Dynamic',
            'create_variant': 'dynamic',
            'value_ids': [
                Command.create({'name': 'dyn1'}),
                Command.create({'name': 'dyn2'}),
            ]
        })


class ProductVariantsCommon(ProductAttributesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_sofa = cls.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'categ_id': cls.product_category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set([
                    cls.color_attribute_red.id,
                    cls.color_attribute_blue.id,
                    cls.color_attribute_green.id
                ])],
            })]
        })

        cls.product_template_shirt = cls.env['product.template'].create({
            'name': 'Shirt',
            'categ_id': cls.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.size_attribute.id,
                    'value_ids': [Command.set([cls.size_attribute_l.id])],
                }),
            ],
        })


class TestProductCommon(ProductVariantsCommon):
    pass
