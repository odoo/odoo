from odoo.tests.common import TransactionCase


class TestProductTemplate(TransactionCase):
    def test_name_search(self):
        partner = self.env['res.partner'].create({
            'name': 'Azure Interior',
        })

        product_tmpl = self.env['product.template'].create({
            'name': 'Rubber Duck',
            'is_storable': True,
            'default_code': 'VOB2A',
            'purchase_ok': True,
        })

        self.env['product.supplierinfo'].create({
            'product_id': product_tmpl.product_variant_id.id,
            'partner_id': partner.id,
            'price': 12.0,
            'delay': 1,
            'product_code': 'VOB2a',
        })
        ns = self.env['product.template'].with_context(partner_id=partner.id).name_search('VOB2', [['purchase_ok', '=', True]])
        self.assertEqual(len(ns), 1, "name_search should have 1 item")
        self.assertEqual(ns[0][1], '[VOB2A] Rubber Duck', "name_search should return the expected result")

    def test_product_purchase_method_with_receive_as_default_purchase_method(self):
        self.env['ir.default'].set('product.template', 'purchase_method', 'receive', company_id=True)

        product = self.env['product.product'].create({'name': 'product_test'})
        self.assertEqual(product.purchase_method, 'receive')

        product.write({'type': 'service'})
        self.assertEqual(product.purchase_method, 'purchase')

        product.write({'type': 'consu'})
        self.assertEqual(product.purchase_method, 'receive')

    def test_product_purchase_method_with_purchase_as_default_purchase_method(self):
        self.env['ir.default'].set('product.template', 'purchase_method', 'purchase', company_id=True)

        product = self.env['product.product'].create({'name': 'product_test'})
        self.assertEqual(product.purchase_method, 'purchase')

        product.write({'type': 'service'})
        self.assertEqual(product.purchase_method, 'purchase')

        product.write({'type': 'consu'})
        self.assertEqual(product.purchase_method, 'purchase')
