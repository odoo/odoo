from odoo.tests.common import TransactionCase


class TestProductTemplate(TransactionCase):
    def test_name_search(self):
      partner = self.env['res.partner'].create({
        'name': 'Azure Interior',
      })

      seller = self.env['product.supplierinfo'].create({
        'name': partner.id,
        'price': 12.0,
        'delay': 1,
        'product_code': 'VOB2a',
      })

      product_tmpl = self.env['product.template'].create({
        'name': 'Rubber Duck',
        'type': 'product',
        'default_code': 'VOB2A',
        'seller_ids': [seller.id],
        'purchase_ok': True,
      })
      ns = self.env['product.template'].with_context(partner_id=partner.id)._name_search('VOB2', [['purchase_ok', '=', True]])
      self.assertEqual(len(ns), 1, "_name_search should have 1 item")
      self.assertEqual(ns[0][1]._value, '[VOB2A] Rubber Duck', "_name_search should return the expected result")
