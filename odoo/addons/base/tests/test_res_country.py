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
