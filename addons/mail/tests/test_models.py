
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # We use an existing model and add monetary information
        partner_model = cls.env['ir.model']._get('res.partner')
        cls.env['ir.model.fields'].create({
            'name': 'x_currency_id',
            'model_id': partner_model.id,
            'ttype': 'many2one',
            'relation': 'res.currency',
        })
        cls.env['ir.model.fields'].create({
            'name': 'x_test_amount',
            'model_id': partner_model.id,
            'ttype': 'monetary',
            'currency_field': 'x_currency_id',
        })
        # Setup company currency by default
        cls.env.company.currency_id = cls.env.ref('base.EUR').id

    def test_find_value_from_field_path_monetary(self):
        """ Check the format of the return in case of monetary value (Digits after comma """
        self.partner_eur = self.env['res.partner'].create({
            'name': 'EUR Partner',
            'x_currency_id': self.env.ref('base.EUR').id,
            'x_test_amount': '150'
        })
        self.partner_jpy = self.env['res.partner'].create({
            'name': 'JPY Partner',
            'x_currency_id': self.env.ref('base.JPY').id,
            'x_test_amount': '150'
        })
        self.partner_lyd = self.env['res.partner'].create({
            'name': 'LYD Partner',
            'x_currency_id': self.env.ref('base.LYD').id,
            'x_test_amount': '150'
        })

        self.assertEqual(self.partner_eur._find_value_from_field_path('x_test_amount'), '150.00')
        self.assertEqual(self.partner_jpy._find_value_from_field_path('x_test_amount'), '150')
        self.assertEqual(self.partner_lyd._find_value_from_field_path('x_test_amount'), '150.000')

    def test_find_value_from_field_path_monetary_empty_value(self):
        """ Check the behavior when a monetary field is False """
        self.partner_no_amount = self.env['res.partner'].create({
            'name': 'Partner No Amount',
            'x_currency_id': self.env.ref('base.EUR').id,
            'x_test_amount': False,
        })

        res = self.partner_no_amount._find_value_from_field_path('x_test_amount')
        self.assertEqual(res, '0.00')

    def test_find_value_from_field_path_monetary_zero_value(self):
        """ Check an amount of 0 is correcly formated"""
        partner = self.env['res.partner'].create({
            'name': 'Partner Zero',
            'x_currency_id': self.env.ref('base.LYD').id,  # 3 décimals
            'x_test_amount': 0.0,
        })
        res = partner._find_value_from_field_path('x_test_amount')
        self.assertEqual(res, '0.000')

    def test_monetary_missing_currency(self):
        """ Check default format is currency_id is not present on record"""
        """ Vérifie le formatage par défaut si aucune devise n'est renseignée sur le record. """
        partner = self.env['res.partner'].create({
            'name': 'Partner No Currency',
            'x_currency_id': False,
            'x_test_amount': 50.0,
        })
        res = partner._find_value_from_field_path('x_test_amount')
        self.assertEqual(res, '50.00')
