import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.product.tests.common import TestProductCommon
from odoo.fields import Command

@odoo.tests.tagged('post_install', '-at_install')
class TestStockProductUpdates(TestPoSCommon, TestProductCommon):

    def setUp(self):
        super(TestStockProductUpdates, self).setUp()
        self.config = self.basic_config
        self.inventory_admin_without_pos = self.env['res.users'].create({
            'name': 'Inventory Admin (No POS access)',
            'login': 'inventory_admin_without_pos',
            'groups_id': [Command.set([self.ref('stock.group_stock_manager')])],
        })
        self.full_admin = self.env['res.users'].create({
            'name': 'Full Admin',
            'login': 'full_admin',
            'groups_id': [
                Command.set(
                    [self.ref('stock.group_stock_manager'),
                     self.ref('point_of_sale.group_pos_manager')]
                )],
        })
        self.product_template = self.env['product.template'].create({
            'name': 'Odoo Juice',
        })

    def test_change_variant_ids(self):
        """
        Ensure user access to create, then links and unlink attribute values 
        from a product template.
        
        Specifically, this test makes sure that these users can create
        and delete attribute values from a product template, especially when
        a product variant has been used in a way that would prevent it from 
        being unlinked (e.g. if it has been used in a stock lot):
        - Inventory + POS admin
        - Inventory admin (No POS access)
        
        Whether or not a product.product record has been used in a stock lot
        impacts whether it will be archived or completely deleted when its 
        attribute value is unlinked from the product template.
        """
        drink_size_attr = self.env['product.attribute'].create({'name': 'Size'})
        attr_value_sm = self.env['product.attribute.value'].with_user(self.full_admin).create({
            'name': 'sm',
            'attribute_id': drink_size_attr.id,
        })
        attr_value_md = self.env['product.attribute.value'].with_user(self.full_admin).create({
            'name': 'md',
            'attribute_id': drink_size_attr.id,
        })
        self.product_template.with_user(self.full_admin).attribute_line_ids = [(0, 0, {
            'attribute_id': drink_size_attr.id,
            'value_ids': [
                Command.link(attr_value_sm.id),
                Command.link(attr_value_md.id), 
            ],
        })]
        
        md_product = self.env['product.product'].search([
            ('product_tmpl_id', '=', self.product_template.id),
            ('product_template_variant_value_ids.product_attribute_value_id', '=', attr_value_md.id),
        ])
        
        # Create a stock lot for the "md" product variant. This should prevent
        # the product variant from being deleted when the attribute value is
        # unlinked from the product template; it should be archived instead.
        self.env['stock.lot'].create({
            'name': 'Lot 1',
            'product_id': md_product.id,
        })
        self.product_template.attribute_line_ids[0].with_user(self.full_admin).value_ids = [
            Command.unlink(attr_value_md.id),
        ]
            
        # Check that the "md" product variant is archived, not deleted. This is
        # important because we need to be able to read, unlink, and create 
        # pos.combo.line records in the case that a product variant is archived.
        self.assertFalse(md_product.active)
            
        # Now as the inventory admin without POS access, try to create and link
        # the "lg" attribute value to the product template.
        attr_value_lg = self.env['product.attribute.value'].with_user(self.inventory_admin_without_pos).create({
            'name': 'lg',
            'attribute_id': drink_size_attr.id,
        })
        self.product_template.attribute_line_ids[0].with_user(self.inventory_admin_without_pos).value_ids = [
            Command.link(attr_value_lg.id),
        ]
        # Finally, ensure that unlinking works without access failure.
        self.product_template.attribute_line_ids[0].with_user(self.inventory_admin_without_pos).value_ids = [
            Command.unlink(attr_value_lg.id),
        ]
        