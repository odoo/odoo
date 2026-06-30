# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class test_res_lang(TransactionCase):

    def test_00_intersperse(self):
        from odoo.addons.base.models.res_lang import intersperse

        assert intersperse("", []) == ("", 0)
        assert intersperse("0", []) == ("0", 0)
        assert intersperse("012", []) == ("012", 0)
        assert intersperse("1", []) == ("1", 0)
        assert intersperse("12", []) == ("12", 0)
        assert intersperse("123", []) == ("123", 0)
        assert intersperse("1234", []) == ("1234", 0)
        assert intersperse("123456789", []) == ("123456789", 0)
        assert intersperse("&ab%#@1", []) == ("&ab%#@1", 0)

        assert intersperse("0", []) == ("0", 0)
        assert intersperse("0", [1]) == ("0", 0)
        assert intersperse("0", [2]) == ("0", 0)
        assert intersperse("0", [200]) == ("0", 0)

        assert intersperse("12345678", [1], '.') == ('1234567.8', 1)
        assert intersperse("12345678", [1], '.') == ('1234567.8', 1)
        assert intersperse("12345678", [2], '.') == ('123456.78', 1)
        assert intersperse("12345678", [2,1], '.') == ('12345.6.78', 2)
        assert intersperse("12345678", [2,0], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [-1,2], '.') == ('12345678', 0)
        assert intersperse("12345678", [2,-1], '.') == ('123456.78', 1)
        assert intersperse("12345678", [2,0,1], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [2,0,0], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [2,0,-1], '.') == ('12.34.56.78', 3)
        assert intersperse("12345678", [3,3,3,3], '.') == ('12.345.678', 2)

        assert intersperse("abc1234567xy", [2], '.') == ('abc1234567.xy', 1)
        assert intersperse("abc1234567xy8", [2], '.') == ('abc1234567x.y8', 1) # ... w.r.t. here.
        assert intersperse("abc12", [3], '.') == ('abc12', 0)
        assert intersperse("abc12", [2], '.') == ('abc12', 0)
        assert intersperse("abc12", [1], '.') == ('abc1.2', 1)

    def test_inactive_users_lang_deactivation(self):
        # activate the language en_GB
        language = self.env['res.lang']._activate_lang('en_GB')

        # assign it to an inactive (new) user
        user = self.env['res.users'].create({
            'name': 'Foo',
            'login': 'foo@example.com',
            'lang': 'en_GB',
            'active': False,
        })

        # make sure it is only used by that user
        self.assertEqual(self.env['res.users'].with_context(active_test=False).search([('lang', '=', 'en_GB')]), user)

        with self.assertRaises(UserError):
            language.active = False

    def test_get_data(self):
        ResLang = self.env['res.lang']
        en_id = ResLang._activate_lang('en_US').id
        en_url_code = ResLang.browse(en_id).url_code
        fr_id = ResLang._activate_lang('fr_FR').id
        fr_direction = ResLang.browse(fr_id).direction
        fr_data = ResLang._get_data(id=fr_id)
        dummy_data = ResLang._get_data(id=0)

        # test __eq__
        self.env.registry.clear_cache()
        self.assertEqual(ResLang._get_data(id=fr_id), fr_data)
        self.assertEqual(ResLang._get_data(id=0), dummy_data)

        # test __bool__
        # data for an active language
        self.assertTrue(ResLang._get_data(code='en_US'))
        # data for an inactive language
        self.assertFalse(ResLang._get_data(code='nl_NL'))
        # data for an invalid dummy language
        self.assertFalse(ResLang._get_data(code='dummy'))

        # test dict conversion
        self.assertEqual(
            dict(ResLang._get_data(id=fr_id)),
            ResLang.browse(fr_id).read(ResLang.CACHED_FIELDS)[0]
        )
        self.assertEqual(
            dict(ResLang._get_data(id=0)),
            dict.fromkeys(ResLang.CACHED_FIELDS, False)
        )

        # test performance
        self.env.cache.clear()
        self.env.registry.clear_cache()
        # 1 query for res_lang +
        # 1 query for ir_attachment to compute `flag_image_url`
        with self.assertQueryCount(2):
            # get cached field value for an active language
            self.assertEqual(ResLang._get_data(code='en_US').url_code, en_url_code)
            # get another cached field value for another active language
            self.assertEqual(ResLang._get_data(code='fr_FR').direction, fr_direction)
            # get field value for an inactive language
            self.assertEqual(ResLang._get_data(code='nl_NL').direction, False)
            # get field value for a dummy language
            self.assertEqual(ResLang._get_data(code='dummy').direction, False)

        # test programming error
        with self.assertRaises(AttributeError):
            # raise error for querying a not cached field of an active language
            ResLang._get_data(code='en_US').flag_image
        with self.assertRaises(AttributeError):
            # raise error for querying a not cached field of an inactive language
            ResLang._get_data(code='nl_NL').flag_image
        with self.assertRaises(AttributeError):
            # raise error for querying a not cached field of the dummy language
            ResLang._get_data(code='dummy').flag_image

    def test_lang_url_code_shortening(self):
        # Setup and initial checks
        ResLang = self.env['res.lang']
        es_ES = self.env.ref('base.lang_es')
        self.assertFalse(es_ES.active)
        self.assertEqual(es_ES.url_code, 'es_ES')
        es_419 = self.env.ref('base.lang_es_419')
        self.assertFalse(es_419.active)
        self.assertEqual(es_419.url_code, 'es')

        # Activating es_ES should give it the url_code 'es' (short version) and
        # es_419 should have its url_code changed from 'es' to 'es_419'
        ResLang._activate_lang('es_ES')
        self.assertEqual(es_419.url_code, 'es_419')
        self.assertEqual(es_ES.url_code, 'es')
        # Activating es_419 should not set it's url_code back to 'es'
        ResLang._activate_lang('es_419')
        self.assertEqual(es_419.url_code, 'es_419')
        self.assertEqual(es_ES.url_code, 'es')
        # Disabling both 'es' languages and activating 'es_419' should set its
        # url_code back to 'es' since that short version is now 'available'
        (es_419 + es_ES).write({'active': False})
        ResLang._activate_lang('es_419')
        self.assertEqual(es_419.url_code, 'es')
        self.assertEqual(es_ES.url_code, 'es_ES')

        # Now, special case if one day a lang receive a short code as default
        # `code`, it's not the case as of today but there is plan to make it
        # happen for `es_419`, the code is already ready for it.
        self.env.cr.execute(f""" UPDATE res_lang SET code = 'es' where id = {es_419.id}""")
        self.env.invalidate_all()
        self.assertEqual(es_419.code, 'es')
        (es_419 + es_ES).write({'active': False})
        ResLang._activate_lang('es_419')
        self.assertEqual(es_419.url_code, 'es')
        self.assertEqual(es_ES.url_code, 'es_ES')
        es_419.active = False
        ResLang._activate_lang('es_ES')
        self.assertEqual(es_419.url_code, 'es')
        # es_ES can't have its url_code shortened because there is no
        # possibility to replace 'es' url_code from 'es_419' if we change its
        # code from 'es_419' to 'es' in the future
        self.assertEqual(es_ES.url_code, 'es_ES')

        # Another special case, /my is reserved to portal controller
        my_MM = ResLang._activate_lang('my_MM')
        self.assertEqual(my_MM.url_code, 'mya')
