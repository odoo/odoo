from odoo.tests import TransactionCase, tagged


class TestResCountryCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.glorious_arstotzka = cls.env['res.country'].create({
            'name': 'Arstotzka',
            'code': 'AA',
        })
        cls.altan = cls.env['res.country.state'].create({
            'country_id': cls.glorious_arstotzka.id,
            'code': 'AL',
            'name': 'Altan',
        })
        cls.yukon = cls.env['res.country'].create({
            'name': 'Yukon Territory',
            'code': 'YY',
        })
        cls.democratic_republic_of_the_congo = cls.env.ref('base.cd')


@tagged('-at_install', 'post_install')
class TestResCountry(TestResCountryCommon):

    def test_name_search_simple(self):
        glorious_arstotzka_tuple = (self.glorious_arstotzka.id, self.glorious_arstotzka.display_name)
        for (name, op) in [
            ('ARSTOTZKA', '='),
            ('arstotzka', '='),
            ('ARSTOTZKA', '!='),
            ('arstotzka', '!='),
            (['ARSTOTZKA'], 'in'),
            (['arstotzka'], 'in'),
            (['ARSTOTZKA'], 'not in'),
            (['arstotzka'], 'not in'),
            ('aA', '='),
            ('aA', '!='),
            (['aA'], 'in'),
            (['aA'], 'not in'),
        ]:
            with self.subTest((name, op)):
                assertFunc = self.assertNotIn if op in ('!=', 'not in') else self.assertEqual
                assertFunc(
                    [glorious_arstotzka_tuple],
                    self.env['res.country'].name_search(name, operator=op),
                    f"Failed on name={name}, operator='{op}'"
                )

    def test_name_search_multi_part_name(self):
        yukon_tuple = (self.yukon.id, self.yukon.display_name)
        for (name, op) in [
            ('YUKON TERRITORY', '='),
            ('yukon territory', '='),
            ('YUKON TERRITORY', '!='),
            ('yukon territory', '!='),
            ('YUKON TERRITORY', 'in'),
            ('yukon territory', 'in'),
            ('YUKON TERRITORY', 'not in'),
            ('yukon territory', 'not in'),
        ]:
            with self.subTest((name, op)):
                assertFunc = self.assertNotIn if op in ('!=', 'not in') else self.assertEqual
                assertFunc(
                    [yukon_tuple],
                    self.env['res.country'].name_search(name, operator=op),
                    f"Failed on name={name}, operator='{op}'"
                )

    def test_name_search_problematic_tokens(self):
        self.skipTest("countries with 'of', 'the', etc(?) in the name will need exact matches")
        drc_tuple = (self.democratic_republic_of_the_congo.id, self.democratic_republic_of_the_congo.display_name)
        for (name, op) in [
            ('DEMOCRATIC REPUBLIC OF THE CONGO', '='),
            ('democratic republic of the congo', '='),
            # etc.
        ]:
            assertFunc = self.assertNotIn if op in ('!=', 'not in') else self.assertEqual
            assertFunc(
                [drc_tuple],
                self.env['res.country'].name_search(name, operator=op),
                f"Failed on name={name}, operator='{op}'"
            )

    def test_name_search_code(self):
        glorious_arstotzka_tuple = (self.glorious_arstotzka.id, self.glorious_arstotzka.display_name)
        yukon_tuple = (self.yukon.id, self.yukon.display_name)
        res = self.env['res.country'].name_search(['yY', 'arstOtzka'], operator='in')
        self.assertEqual(res, [glorious_arstotzka_tuple, yukon_tuple])
        res = self.env['res.country'].name_search(('Yy', 'arStOtzKA'), operator='not in')
        self.assertFalse(glorious_arstotzka_tuple in res)
        self.assertFalse(yukon_tuple in res)


@tagged('-at_install', 'post_install')
class TestResCountryState(TestResCountryCommon):

    def test_name_search_ilike(self):
        """It should be possible to find a state by its display name
        """
        glorious_arstotzka = self.glorious_arstotzka
        altan = self.altan
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
