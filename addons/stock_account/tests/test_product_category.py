from odoo.tests.common import TransactionCase
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestProductCategory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bookkeeper_user = cls.env['res.users'].create({
            'name': "Bookkeeper User",
            'login': "bookkeeper_user",
            'email': "bookkeeper@example.com",
            'group_ids': [(6, 0, [
                cls.env.ref('product.group_product_manager').id,
                cls.env.ref('account.group_account_user').id,
            ])],
        })

    def test_create_category_as_bookkeeper(self):
        """Test that a user without account manager rights can create a product category"""
        with Form(self.env['product.category'].with_user(self.bookkeeper_user)) as categ_form:
            categ_form.name = 'Test Category'
            category = categ_form.save()
        self.assertTrue(category.exists())
