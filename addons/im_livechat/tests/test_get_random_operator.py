import odoo
from odoo.tests import HttpCase
from odoo.tests.common import new_test_user
from unittest.mock import patch
from odoo.addons.bus.models.res_users import ResUsers

def _compute_im_status(self):
    for record in self:
        record.im_status = 'online'


@odoo.tests.tagged('-at_install', 'post_install')
@patch.object(ResUsers, '_compute_im_status', _compute_im_status)
class TestGetRandomOperator(HttpCase):
    def _create_operator(self, lang_code=None, country_code=None):
        operator = new_test_user(self.env, login=f'operator_{lang_code or country_code}_{self.operator_id}')
        operator.partner_id = self.env['res.partner'].create({
            'name': f'Operator {lang_code or country_code}',
            'lang': lang_code,
            'country_id': self.env['res.country'].search([('code', '=', country_code)]).id if country_code else None,
        })
        self.operator_id += 1
        return operator

    def setUp(self):
        super().setUp()
        self.operator_id = 0
        self.env['res.lang'].with_context(active_test=False).search([
            ('code', 'in', ['fr_FR', 'es_ES', 'de_DE', 'en_US'])
        ]).write({'active': True})

    def test_get_by_lang(self):
        fr_operator = self._create_operator('fr_FR')
        en_operator = self._create_operator('en_US')
        livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'Livechat Channel',
            'user_ids': [fr_operator.id, en_operator.id],
        })
        self.assertEqual(fr_operator, livechat_channel._get_random_operator(lang='fr_FR'))
        self.assertEqual(en_operator, livechat_channel._get_random_operator(lang='en_US'))

    def test_get_by_lang_no_operator_matching_lang(self):
        fr_operator = self._create_operator('fr_FR')
        livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'Livechat Channel',
            'user_ids': [fr_operator.id],
        })
        self.assertEqual(fr_operator, livechat_channel._get_random_operator(lang='en_US'))

    def test_get_by_country(self):
        fr_operator = self._create_operator(country_code='FR')
        en_operator = self._create_operator(country_code='US')
        livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'Livechat Channel',
            'user_ids': [fr_operator.id, en_operator.id],
        })
        self.assertEqual(
            fr_operator,
            livechat_channel._get_random_operator(country_id=self.env['res.country'].search([('code', '=', 'FR')]).id)
        )
        self.assertEqual(
            en_operator,
            livechat_channel._get_random_operator(country_id=self.env['res.country'].search([('code', '=', 'US')]).id)
        )

    def test_get_by_country_no_operator_matching_country(self):
        fr_operator = self._create_operator(country_code='FR')
        livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'Livechat Channel',
            'user_ids': [fr_operator.id],
        })
        self.assertEqual(
            fr_operator,
            livechat_channel._get_random_operator(country_id=self.env['res.country'].search([('code', '=', 'US')]).id)
        )

    def test_get_by_lang_and_country_prioritize_lang(self):
        fr_operator = self._create_operator('fr_FR', 'FR')
        en_operator = self._create_operator('en_US', 'US')
        livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'Livechat Channel',
            'user_ids': [fr_operator.id, en_operator.id],
        })
        self.assertEqual(
            fr_operator,
            livechat_channel._get_random_operator(lang='fr_FR', country_id=self.env['res.country'].search([('code', '=', 'US')]).id)
        )
        self.assertEqual(
            en_operator,
            livechat_channel._get_random_operator(lang='en_US', country_id=self.env['res.country'].search([('code', '=', 'FR')]).id)
        )
