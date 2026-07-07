from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProductTemplateCabys(TransactionCase):

    def test_valid_cabys_is_accepted(self):
        product = self.env['product.template'].create({
            'name': 'Producto válido', 'l10n_cr_fe_cabys': '0111101000000',
        })
        self.assertEqual(product.l10n_cr_fe_cabys, '0111101000000')

    def test_invalid_cabys_length_raises(self):
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Producto inválido', 'l10n_cr_fe_cabys': '123',
            })

    def test_invalid_cabys_non_digit_raises(self):
        with self.assertRaises(ValidationError):
            self.env['product.template'].create({
                'name': 'Producto inválido', 'l10n_cr_fe_cabys': 'abcdefghijklm',
            })
