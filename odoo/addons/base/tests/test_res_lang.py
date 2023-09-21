# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from psycopg2 import IntegrityError

from odoo.tests.common import TransactionCase
from odoo.tools import translate_sql_constraint, mute_logger


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

    @mute_logger('odoo.sql_db')
    def test_unique(self):
        lang = self.env['res.lang']
        for field_name, msg in [
            ('name', "The name of the language must be unique!"),
            ('code', "The code of the language must be unique!"),
            ('url_code', "The URL code of the language must be unique!"),
        ]:
            try:
                with self.env.cr.savepoint():
                    lang.create({'name': 'l1', 'code': 'l1', 'url_code': 'l1', field_name: 'XXX'})
                    lang.create({'name': 'l2', 'code': 'l2', 'url_code': 'l2', field_name: 'XXX'})
            except IntegrityError as e:
                self.assertIn(e.diag.constraint_name, self.env.registry._sql_constraints)
                e = translate_sql_constraint(self.env.cr, e.diag.constraint_name, 'en_US')
                self.assertEqual(str(e), msg)
            else:
                self.fail("Should have raised an integrity error")
