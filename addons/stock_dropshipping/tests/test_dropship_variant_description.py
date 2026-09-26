# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDropshipVariantDescription(TransactionCase):
    """Regression for the language of the no-variant/custom attribute block on a
    dropship purchase order line.

    On a dropship, the sale order is written in the customer's language while the
    generated purchase order (line name) is written in the vendor's language. The
    appended "Attribute: Value" block used to keep the customer's language even
    when the vendor-language translations existed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('sv_SE')
        cls.env['res.lang']._activate_lang('en_GB')

        # Customer speaks Swedish, vendor speaks British English.
        cls.customer = cls.env['res.partner'].create({'name': 'Customer', 'lang': 'sv_SE'})
        cls.vendor = cls.env['res.partner'].create({'name': 'Vendor', 'lang': 'en_GB'})

        # A no-variant attribute with two values so the block is emitted
        # (value_count > 1), and translations in both languages.
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

        cls.dropship_route = cls.env.ref('stock_dropshipping.route_drop_shipping')
        cls.product_template = cls.env['product.template'].create({
            'name': 'Dropship Product',
            'is_storable': True,
            'route_ids': [Command.set(cls.dropship_route.ids)],
            'seller_ids': [Command.create({'partner_id': cls.vendor.id, 'min_qty': 0.0})],
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set((cls.color_attribute.value_ids).ids)],
            })],
        })
        cls.product = cls.product_template.product_variant_id
        cls.red_ptav = cls.product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == cls.value_red
        )

    def _confirm_dropship_so(self):
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'partner_invoice_id': self.customer.id,
            'partner_shipping_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'product_no_variant_attribute_value_ids': [Command.set(self.red_ptav.ids)],
            })],
        })
        so.action_confirm()
        po = self.env['purchase.order'].search([('group_id', '=', so.procurement_group_id.id)])
        self.assertEqual(len(po.order_line), 1, "The dropship SO must generate one PO line")
        return so, po

    def test_dropship_po_line_variant_block_uses_vendor_language(self):
        so, po = self._confirm_dropship_so()
        so_line = so.order_line
        po_line = po.order_line

        # Control: the sale order line keeps the customer's (Swedish) language.
        self.assertIn('Färg: Röd', so_line.name,
                      "The SO line block must stay in the customer's language")

        # Fix: the PO line variant block is rendered in the vendor's (British
        # English) language, matching the vendor-language product name.
        self.assertIn('Colour: Red', po_line.name,
                      "The PO line block must be rendered in the vendor's language")
        self.assertNotIn('Färg: Röd', po_line.name,
                         "The PO line block must not stay in the customer's language")
        self.assertNotIn('Röd', po_line.name,
                         "No Swedish value should leak onto the PO line")
