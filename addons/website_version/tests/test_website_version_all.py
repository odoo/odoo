from . import test_website_version_base
from openerp.osv.orm import except_orm
from openerp.http import request

class TestWebsiteVersionAll(test_website_version_base.TestWebsiteVersionBase):

    def test_copy_snapshot(self):
        """ Testing Snapshot_copy"""
        cr, uid, view_0_0_0_0_id, snapshot_id, website_id = self.cr, self.uid, self.view_0_0_0_0_id, self.snapshot_id, self.website_id

        copy_snapshot_id = self.snapshot.create(cr, uid,{'name':'copy_snapshot_0_0_0_0', 'website_id':website_id}, context=None)
        self.ir_ui_view.copy_snapshot(cr, uid, snapshot_id,copy_snapshot_id,context=None)
        copy_snapshot = self.snapshot.browse(cr, uid, [copy_snapshot_id], context=None)[0]
        view_copy_snapshot=copy_snapshot.view_ids[0]
        view_0_0_0_0 = self.ir_ui_view.browse(cr, uid, [view_0_0_0_0_id], context={'snapshot_id':snapshot_id})[0]
        self.assertEqual(view_copy_snapshot.arch, view_0_0_0_0.arch, 'website_version: copy_snapshot: website_version must have in snpashot_copy the same views then in snapshot_0_0_0_0')
        