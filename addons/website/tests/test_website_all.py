from . import test_website_base
from openerp.http import request
from openerp.osv.orm import except_orm

class TestWebsiteAll(test_website_base.TestWebsiteBase):

    def test_read_a_master_view(self):
        """ Testing read a master view """
        from pudb import set_trace; set_trace()
        cr, uid, master_view_key, default_website_id, default_website, res_company_object = self.cr, self.uid, self.master_view_key, self.default_website_id, self.default_website, self.res_company_object
        request.httprequest.path = 'homepage'

        result = self.ir_ui_view.render(cr, uid, master_view_key, values={'website': default_website, 'res_company': res_company_object},
            engine='ir.qweb',
            context={
                'website_id': default_website_id,
                'lang': 'en_US', 
                'tz': None})
        #self.assertEqual(result[0]['arch'], arch_0_0_0_0, 'website_version: read: website_version must read the homepage_0_0_0_0 which is in the snapshot_0_0_0_0')

        print 'TEST'
        print result
