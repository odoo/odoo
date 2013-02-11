import unittest2

import openerp.tests.common as common

class test_res_lang(common.TransactionCase):

    def test_00(self):
        from openerp.addons.base.res.res_lang import original_group, intersperse

        for g in [original_group, intersperse]:
            # print "asserts on", g.func_name
            assert g("", []) == ("", 0), "Assert passed"
            assert g("0", []) == ("0", 0), "Assert passed"
            assert g("012", []) == ("012", 0), "Assert passed"
            assert g("1", []) == ("1", 0), "Assert passed"
            assert g("12", []) == ("12", 0), "Assert passed"
            assert g("123", []) == ("123", 0), "Assert passed"
            assert g("1234", []) == ("1234", 0), "Assert passed"
            assert g("123456789", []) == ("123456789", 0), "Assert passed"
            assert g("&ab%#@1", []) == ("&ab%#@1", 0), "Assert passed"

            assert g("0", []) == ("0", 0), "Assert passed"
            assert g("0", [1]) == ("0", 0), "Assert passed"
            assert g("0", [2]) == ("0", 0), "Assert passed"
            assert g("0", [200]) == ("0", 0), "Assert passed"

            # breaks original_group:
            if g.func_name == 'intersperse':
                assert g("12345678", [0], '.') == ('12345678', 0)
                assert g("", [1], '.') == ('', 0)
            assert g("12345678", [1], '.') == ('1234567.8', 1)
            assert g("12345678", [1], '.') == ('1234567.8', 1)
            assert g("12345678", [2], '.') == ('123456.78', 1)
            assert g("12345678", [2,1], '.') == ('12345.6.78', 2)
            assert g("12345678", [2,0], '.') == ('12.34.56.78', 3)
            assert g("12345678", [-1,2], '.') == ('12345678', 0)
            assert g("12345678", [2,-1], '.') == ('123456.78', 1)
            assert g("12345678", [2,0,1], '.') == ('12.34.56.78', 3)
            assert g("12345678", [2,0,0], '.') == ('12.34.56.78', 3)
            assert g("12345678", [2,0,-1], '.') == ('12.34.56.78', 3)
            assert g("12345678", [3,3,3,3], '.') == ('12.345.678', 2)

        assert original_group("abc1234567xy", [2], '.') == ('abc1234567.xy', 1)
        assert original_group("abc1234567xy8", [2], '.') == ('abc1234567xy8', 0) # difference here...
        assert original_group("abc12", [3], '.') == ('abc12', 0)
        assert original_group("abc12", [2], '.') == ('abc12', 0)
        assert original_group("abc12", [1], '.') == ('abc1.2', 1)

        assert intersperse("abc1234567xy", [2], '.') == ('abc1234567.xy', 1)
        assert intersperse("abc1234567xy8", [2], '.') == ('abc1234567x.y8', 1) # ... w.r.t. here.
        assert intersperse("abc12", [3], '.') == ('abc12', 0)
        assert intersperse("abc12", [2], '.') == ('abc12', 0)
        assert intersperse("abc12", [1], '.') == ('abc1.2', 1)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
