from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestResCountryState(TransactionCase):
    def test_find_by_name(self):
        """It should be possible to find a state by its display name
        """
        glorious_arstotzka = self.env['res.country'].create({
            'name': 'Arstotzka',
            'code': 'AA',
        })
        altan = self.env['res.country.state'].create({
            'country_id': glorious_arstotzka.id,
            'code': 'AL',
            'name': 'Altan',
        })

        for name in [
            altan.name,
            altan.display_name,
            'Altan(AA)',
            'Altan ( AA )',
            'Altan (Arstotzka)',
            'Altan (Arst)', # dubious
        ]:
            with self.subTest(name):
                self.assertEqual(
                    self.env['res.country.state'].name_search(name, operator='='),
                    [(altan.id, altan.display_name)]
                )

        # imitates basque provinces
        vescillo = self.env['res.country.state'].create({
            'country_id': glorious_arstotzka.id,
            'code': 'VE',
            'name': "Vescillo (Vesilo)",
        })
        for name in [
            vescillo.name,
            vescillo.display_name,
            "vescillo",
            "vesilo",
            "vescillo (AA)",
            "vesilo (AA)",
            "vesilo (Arstotzka)",
        ]:
            with self.subTest(name):
                # note operator for more flexible state name matching
                self.assertEqual(
                    self.env['res.country.state'].name_search(name, operator='ilike'),
                    [(vescillo.id, vescillo.display_name)]
                )

        # search in state list
        for name in [
            [altan.name],
            [altan.display_name],
            ['Altan(AA)'],
            ['Altan ( AA )'],
            ['Altan (Arstotzka)'],
            ['Altan (Arst)'],
        ]:
            with self.subTest(name):
                self.assertEqual(
                    self.env['res.country.state'].name_search(name, operator='in'),
                    [(altan.id, altan.display_name)]
                )


@tagged('-at_install', 'post_install')
class TestResCountry(TransactionCase):
    def test_search_name_longer_than_code(self):
        """A name longer than the code size should not match the code of
        another country made of its first characters (GERMANY vs GE)
        """
        Country = self.env['res.country']
        germany = self.env.ref('base.de')
        georgia = self.env.ref('base.ge')
        germany.name = 'GERMANY'

        self.assertEqual(Country.name_search('GERMANY', operator='='), [(germany.id, 'GERMANY')])
        self.assertEqual(Country.search([('display_name', 'in', ['GERMANY'])]), germany)
        self.assertIn(georgia, Country.search([('display_name', '!=', 'GERMANY')]))

        result = self.env['res.partner'].load(['name', 'country_id'], [['Partner A', 'GERMANY']])
        self.assertFalse(result['messages'])
        self.assertEqual(self.env['res.partner'].browse(result['ids']).country_id, germany)
