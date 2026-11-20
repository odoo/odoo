from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestFavoriteColors(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({
            'name': 'Company A',
            'favorite_colors': ['#FF9C00', '#00FFFF80'],
        })
        cls.company_b = cls.env['res.company'].create({'name': 'Company B'})
        cls.user = new_test_user(
            cls.env,
            login='favorite_colors_user',
            company_id=cls.company_a.id,
            company_ids=[cls.company_a.id, cls.company_b.id],
        )

    def test_favorite_colors_must_be_uppercase_hexadecimal_colors(self):
        for invalid_colors in (
            '#FF9C00',
            ['#ff9c00'],
            ['#FF9C0'],
            ['red'],
            ['rgb(255, 156, 0)'],
            [255],
        ):
            with self.subTest(colors=invalid_colors), self.assertRaises(ValidationError):
                self.company_b.favorite_colors = invalid_colors
        self.company_b.favorite_colors = []
        self.company_b.favorite_colors = ['#FF9C00', '#FF9C0080']

    def test_favorite_colors_in_session_info(self):
        self.authenticate(self.user.login, self.user.login)
        session_info = self.make_jsonrpc_request('/web/session/get_session_info')
        allowed_companies = session_info['user_companies']['allowed_companies']
        self.assertEqual(
            allowed_companies[str(self.company_a.id)]['favorite_colors'],
            ['#FF9C00', '#00FFFF80'],
        )
        self.assertEqual(allowed_companies[str(self.company_b.id)]['favorite_colors'], [])

    def test_add_and_remove_favorite_colors(self):
        self.assertEqual(self.company_b.add_favorite_color('#ff9c00'), ['#FF9C00'])
        self.assertEqual(self.company_b.add_favorite_color('#00FFFF'), ['#FF9C00', '#00FFFF'])
        # A color already in the favorites is not added twice.
        self.assertEqual(self.company_b.add_favorite_color('#FF9C00'), ['#FF9C00', '#00FFFF'])
        self.assertEqual(self.company_b.remove_favorite_color('#ff9c00'), ['#00FFFF'])
        self.assertEqual(self.company_b.remove_favorite_color('#FF9C00'), ['#00FFFF'])
        self.assertEqual(self.company_b.remove_favorite_color('#00FFFF'), [])
        with self.assertRaises(ValidationError):
            self.company_b.add_favorite_color('red')

    def test_favorite_colors_require_the_right_to_edit_the_company(self):
        self.assertFalse(self.user._is_admin())
        company_a = self.company_a.with_user(self.user)
        self.assertEqual(company_a.favorite_colors, ['#FF9C00', '#00FFFF80'])
        with self.assertRaises(AccessError):
            company_a.add_favorite_color('#B5D6A5')
        with self.assertRaises(AccessError):
            company_a.remove_favorite_color('#FF9C00')
