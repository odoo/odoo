import unittest2

import openerp.tests.common as common
from openerp.osv.orm import except_orm

class test_res_lang(common.TransactionCase):

    def test_00_intersperse(self):
        from openerp.addons.base.res.res_lang import intersperse

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
        
        
    def test_00_language_translation(self):
        
        cr, uid = self.cr, self.uid
        #usefull models
        base_lang_obj = self.registry('base.language.install')
        lang_obj = self.registry('res.lang')
        user_obj = self.registry('res.users')
        ir_values = self.registry['ir.values']
        ir_values.set_default(cr, uid, 'res.partner', 'lang', 'en_US')
        user_lang = user_obj.browse(cr, uid, uid, context=None).lang
        context = {'uid': uid, 'lang': user_lang}
        #Check only one language is enabled.
        lang_count = lang_obj.search(cr, uid, [('active', '=', True)], count=True)
        assert lang_count <= 1, "More then one language are enabled"
        
        """Test case for load new language and deactive and Check constraint for at least one language should be enabled """
        #Load new French language from base language wizard
        lang_id = base_lang_obj.create(cr, uid, {'lang': 'fr_BE'})
        base_lang_obj.lang_install(cr, uid, [lang_id], context=context)

        #Check status of french language
        fr_lang_id = lang_obj.search(cr, uid, [('code', '=', 'fr_BE')], context=context)
        lang = lang_obj.browse(cr, uid, fr_lang_id, context=context)
        lang_obj.write(cr, uid, fr_lang_id, {'active': True}, context=context)

        #Deactive French language
        lang_obj.set_status(cr, uid, fr_lang_id, context=context)

        #Try to Deactive English language
        en_lang_id = lang_obj.search(cr, uid, [('code', '=', 'en_US')], context=context)
        with self.assertRaises(except_orm):
            lang_obj.set_status(cr, uid, en_lang_id, context=context)
        """Test case for Check translation term if multiple language enabled"""
        lang_count = lang_obj.search(cr, uid, [('active', '=', True)], count=True)
        assert lang_count <= 1, "More then one language are enabled"
