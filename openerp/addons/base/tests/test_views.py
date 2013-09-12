import unittest2

import openerp.tests.common as common
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

class test_views(common.TransactionCase):

    @mute_logger('openerp.osv.orm', 'openerp.addons.base.ir.ir_ui_view')
    def test_00_init_check_views(self):
        Views = self.registry('ir.ui.view')

        self.assertTrue(Views.pool._init)

        error_msg = "Invalid XML for View Architecture"
        # test arch check is call for views without xmlid during registry initialization
        with self.assertRaisesRegexp(except_orm, error_msg):
            Views.create(self.cr, self.uid, {
                'name': 'Test View #1',
                'model': 'ir.ui.view',
                'arch': """<?xml version="1.0"?>
                            <tree>
                              <field name="test_1"/>
                            </tree>
                        """,
            })

        # same for inherited views
        with self.assertRaisesRegexp(except_orm, error_msg):
            # Views.pudb = True
            Views.create(self.cr, self.uid, {
                'name': 'Test View #2',
                'model': 'ir.ui.view',
                'inherit_id': self.browse_ref('base.view_view_tree').id,
                'arch': """<?xml version="1.0"?>
                            <xpath expr="//field[@name='name']" position="after">
                              <field name="test_2"/>
                            </xpath>
                        """,
            })


if __name__ == '__main__':
    unittest2.main()
