from . import test_website_version_base
from openerp.osv.orm import except_orm
from openerp.http import request

class TestWebsiteVersionAll(test_website_version_base.TestWebsiteVersionBase):

    def test_copy_version(self):
        """ Testing version_copy"""
        cr, uid, view_0_0_0_0_id, version_id, website_id = self.cr, self.uid, self.view_0_0_0_0_id, self.version_id, self.website_id

        copy_version_id = self.version.create(cr, uid,{'name':'copy_version_0_0_0_0', 'website_id':website_id}, context=None)
        self.ir_ui_view.copy_version(cr, uid, version_id,copy_version_id,context=None)
        copy_version = self.version.browse(cr, uid, [copy_version_id], context=None)[0]
        view_copy_version=copy_version.view_ids[0]
        view_0_0_0_0 = self.ir_ui_view.browse(cr, uid, [view_0_0_0_0_id], context={'version_id':version_id})[0]
        self.assertEqual(view_copy_version.arch, view_0_0_0_0.arch, 'website_version: copy_version: website_version must have in snpashot_copy the same views then in version_0_0_0_0')
        