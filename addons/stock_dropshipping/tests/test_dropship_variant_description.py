# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDropshipVariantDescription(TransactionCase):
    """The attribute block of a dropship PO line must use the vendor's language."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('sv_SE')
        cls.env['res.lang']._activate_lang('en_GB')

        cls.customer = cls.env['res.partner'].create({'name': 'Customer', 'lang': 'sv_SE'})
        cls.vendor = cls.env['res.partner'].create({'name': 'Vendor', 'lang': 'en_GB'})

        # Two values so that the no-variant attribute is part of the description.
        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Red'}),
                Command.create({'name': 'Blue'}),
            ],
        })
        cls.value_red = cls.color_attribute.value_ids.filtered(lambda v: v.name == 'Red')
        cls.color_attribute.with_context(lang='sv_SE').name = 'Färg'
        cls.color_attribute.with_context(lang='en_GB').name = 'Colour'
        cls.value_red.with_context(lang='sv_SE').name = 'Röd'
        cls.value_red.with_context(lang='en_GB').name = 'Red'

        cls.product_template = cls.env['product.template'].create({
            'name': 'Dropship Product',
            'is_storable': True,
            'route_ids': [Command.set(cls.env.ref('stock_dropshipping.route_drop_shipping').ids)],
            'seller_ids': [Command.create({'partner_id': cls.vendor.id, 'min_qty': 0.0})],
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set(cls.color_attribute.value_ids.ids)],
            })],
        })
        cls.red_ptav = cls.product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == cls.value_red
        )

    def test_dropship_po_line_variant_block_uses_vendor_language(self):
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.product_template.product_variant_id.id,
                'product_uom_qty': 1.0,
                'product_no_variant_attribute_value_ids': [Command.set(self.red_ptav.ids)],
            })],
        })
        so.action_confirm()
        po_line = so._get_purchase_orders().order_line
        self.assertEqual(len(po_line), 1)

        self.assertIn('Färg: Röd', so.order_line.name, "The SO line keeps the customer's language")
        self.assertIn('Colour: Red', po_line.name, "The PO line uses the vendor's language")
        self.assertNotIn('Röd', po_line.name)
