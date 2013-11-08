from functools import partial
import unittest2

import openerp.tests.common as common
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

class test_views(common.TransactionCase):

    @mute_logger('openerp.osv.orm', 'openerp.addons.base.ir.ir_ui_view')
    def test_00_init_check_views(self):
        Views = self.registry('ir.ui.view')

        self.assertTrue(Views.pool._init)

        error_msg = "The model name does not exist or the view architecture cannot be rendered"
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

    def test_20_remove_unexisting_attribute(self):
        Views = self.registry('ir.ui.view')
        Views.create(self.cr, self.uid, {
            'name': 'Test View',
            'model': 'ir.ui.view',
            'inherit_id': self.browse_ref('base.view_view_tree').id,
            'arch': """<?xml version="1.0"?>
                        <xpath expr="//field[@name='name']" position="attributes">
                            <attribute name="non_existing_attribute"></attribute>
                        </xpath>
                    """,
        })

    def _insert_view(self, **kw):
        """Insert view into database via a query to passtrough validation"""
        kw.pop('id', None)

        keys = sorted(kw.keys())
        fields = ','.join('"%s"' % (k.replace('"', r'\"'),) for k in keys)
        params = ','.join('%%(%s)s' % (k,) for k in keys)

        query = 'INSERT INTO ir_ui_view(%s) VALUES(%s) RETURNING id' % (fields, params)
        self.cr.execute(query, kw)
        return self.cr.fetchone()[0]

    def test_10_validate_custom_views(self):
        Views = self.registry('ir.ui.view')
        model = 'ir.actions.act_url'

        validate = partial(Views._validate_custom_views, self.cr, self.uid, model)

        # validation of a single view
        vid = self._insert_view(**{
            'name': 'base view',
            'model': model,
            'priority': 1,
            'arch': """<?xml version="1.0"?>
                        <tree string="view">
                          <field name="url"/>
                        </tree>
                    """,
        })
        self.assertTrue(validate())     # single view

        # validation of a inherited view
        self._insert_view(**{
            'name': 'inherited view',
            'model': model,
            'priority': 1,
            'inherit_id': vid,
            'arch': """<?xml version="1.0"?>
                        <xpath expr="//field[@name='url']" position="before">
                          <field name="name"/>
                        </xpath>
                    """,
        })
        self.assertTrue(validate())     # inherited view

        # validation of a bad inherited view
        self._insert_view(**{
            'name': 'bad inherited view',
            'model': model,
            'priority': 2,
            'inherit_id': vid,
            'arch': """<?xml version="1.0"?>
                        <xpath expr="//field[@name='url']" position="after">
                          <field name="bad"/>
                        </xpath>
                    """,
        })
        with mute_logger('openerp.osv.orm', 'openerp.addons.base.ir.ir_ui_view'):
            self.assertFalse(validate())    # bad inherited view


if __name__ == '__main__':
    unittest2.main()
