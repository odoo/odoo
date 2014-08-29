from openerp.tests import common

class TestWebsiteBase(common.TransactionCase):

    def setUp(self):
        super(TestWebsiteBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_ui_view = self.registry('ir.ui.view')
        self.website = self.registry('website')

        #Usefull objects
        master_view_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'homepage')
        self.master_view_id = master_view_ref and master_view_ref[1] or False
        self.master_view_key = self.ir_ui_view.browse(cr, uid, [self.master_view_id], context=None)[0].key
        self.arch_master = self.ir_ui_view.browse(cr, uid, [self.master_view_id], context=None)[0].arch

        view_0_0_0_0_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'homepage')
        self.view_0_0_0_0_id = view_0_0_0_0_ref and view_0_0_0_0_ref[1] or False
        self.view_0_0_0_0_key = self.ir_ui_view.browse(cr, uid, [self.view_0_0_0_0_id], context=None)[0].key
        self.arch_0_0_0_0 = self.ir_ui_view.browse(cr, uid, [self.view_0_0_0_0_id], context=None)[0].arch

        view_common_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'aboutus')
        self.view_common_id = view_0_0_0_0_ref and view_common_ref[1] or False
        self.view_common_key = self.ir_ui_view.browse(cr, uid, [self.view_common_id], context=None)[0].key
        self.arch_common = self.ir_ui_view.browse(cr, uid, [self.view_common_id], context=None)[0].arch

        default_website_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'default_website')
        self.default_website_id = default_website_ref and default_website_ref[1] or False
        self.default_website = self.website.browse(cr, uid, [self.default_website_id], context=None)[0]
        
        second_website_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'website', 'second_website')
        self.second_website_id = second_website_ref and second_website_ref[1] or False
        