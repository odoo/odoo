import unittest2

import openerp.tests.common as common

class test_res_config(common.TransactionCase):

    def setUp(self):
        super(test_res_config, self).setUp()
        self.res_config = self.registry('res.config.settings')
        self.menu_xml_id = 'base.menu_action_res_users'

    def test_00_get_option_path(self):
        """ The get_option_path() should return a tuple containing a string and an integer """
        res = self.res_config.get_option_path(self.cr, self.uid, self.menu_xml_id, context=None)

        # Check types
        self.assertTrue(isinstance(res, tuple)), "The result of get_option_path() should be a tuple (got %s)" % type(res)
        self.assertTrue(len(res) == 2), "The tuple should contain 2 elements (got %s)" % len(res)
        self.assertTrue(isinstance(res[0], basestring)), "The first element of the tuple should be a string (got %s)" % type(res[0])
        self.assertTrue(isinstance(res[1], long)), "The second element of the tuple should be an long (got %s)" % type(res[1])

        # Check returned values
        module_name, menu_xml_id = self.menu_xml_id.split('.')
        dummy, menu_id = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, module_name, menu_xml_id)
        ir_ui_menu = self.registry('ir.ui.menu').browse(self.cr, self.uid, menu_id, context=None)

        self.assertTrue(res[0] == ir_ui_menu.complete_name), "Result mismatch: expected %s, got %s" % (ir_ui_menu.complete_name, res[0])
        self.assertTrue(res[1] == ir_ui_menu.action.id), "Result mismatch: expected %s, got %s" % (ir_ui_menu.action.id, res[1])
