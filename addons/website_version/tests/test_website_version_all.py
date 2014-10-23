from . import test_website_version_base
from openerp.osv.orm import except_orm
from openerp.http import request

class TestWebsiteVersionAll(test_website_version_base.TestWebsiteVersionBase):

    def test_read_with_right_context(self):
        """ Testing Read with right context """
        cr, uid, master_view_id, snapshot_id, arch_0_0_0_0, website_id= self.cr, self.uid, self.master_view_id, self.snapshot_id, self.arch_0_0_0_0, self.website_id
        # def loader(name):
        #     return self.ir_ui_view.read_template(cr, uid, name, context={'website_id':website_id, 'snapshot_id':1})
        # result = self.ir_qweb.render(cr, uid, 'website.homepage', qwebcontext=None, loader=loader, context={'website_id':website_id, 'snapshot_id':1})
        result = self.ir_ui_view.render(cr, uid, 'website.homepage', values=None, engine='website.qweb', context={'website_id':website_id, 'snapshot_id':1})
        print result

        # result = self.ir_ui_view.read(cr, uid, [master_view_id], ['arch'], load='_classic_read')
        # self.assertEqual(result[0]['arch'], arch_0_0_0_0, 'website_version: read: website_version must read the homepage_0_0_0_0 which is in the snapshot_0_0_0_0')

    def test_copy_snapshot(self):
        """ Testing Snapshot_copy"""
        cr, uid, view_0_0_0_0_id, snapshot_id, website_id = self.cr, self.uid, self.view_0_0_0_0_id, self.snapshot_id, self.website_id

        copy_snapshot_id = self.snapshot.create(cr, uid,{'name':'copy_snapshot_0_0_0_0', 'website_id':website_id}, context=None)
        self.ir_ui_view.copy_snapshot(cr, uid, snapshot_id,copy_snapshot_id,context=None)
        copy_snapshot = self.snapshot.browse(cr, uid, [copy_snapshot_id], context=None)[0]
        view_copy_snapshot=copy_snapshot.view_ids[0]
        view_0_0_0_0 = self.ir_ui_view.browse(cr, uid, [view_0_0_0_0_id], context={'snapshot_id':snapshot_id})[0]
        self.assertEqual(view_copy_snapshot.arch, view_0_0_0_0.arch, 'website_version: copy_snapshot: website_version must have in snpashot_copy the same views then in snapshot_0_0_0_0')
        