from functools import partial
import unittest2

import lxml.etree
from lxml.builder import E

import openerp.tests.common as common
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

class test_views(common.TransactionCase):

    @mute_logger('openerp.osv.orm', 'openerp.addons.base.ir.ir_ui_view')
    def test_whatever(self):
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

    def test_nonexistent_attribute_removal(self):
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

    def test_custom_view_validation(self):
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

    def test_view_inheritance(self):
        Views = self.registry('ir.ui.view')

        v1 = Views.create(self.cr, self.uid, {
            'name': "bob",
            'model': 'ir.ui.view',
            'arch': """
                <form string="Base title" version="7.0">
                    <separator string="separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button"/>
                        or
                        <button string="Skip" special="cancel" />
                    </footer>
                </form>
            """
        })
        v2 = Views.create(self.cr, self.uid, {
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': v1,
            'arch': """
                <data>
                    <form position="attributes" version="7.0">
                        <attribute name="string">Replacement title</attribute>
                    </form>
                    <footer position="replace">
                        <footer>
                            <button name="action_next" type="object" string="New button"/>
                        </footer>
                    </footer>
                    <separator string="separator" position="replace">
                        <p>Replacement data</p>
                    </separator>
                </data>
            """
        })
        v3 = Views.create(self.cr, self.uid, {
            'name': 'jake',
            'model': 'ir.ui.view',
            'inherit_id': v1,
            'priority': 17,
            'arch': """
                <footer position="attributes">
                    <attribute name="thing">bob</attribute>
                </footer>
            """
        })

        view = self.registry('ir.ui.view').fields_view_get(
            self.cr, self.uid, v2, view_type='form', context={
                # fucking what?
                'check_view_ids': [v2, v3]
            })
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            lxml.etree.tostring(lxml.etree.fromstring(
                view['arch'],
                parser=lxml.etree.XMLParser(remove_blank_text=True)
            )),
            '<form string="Replacement title" version="7.0">'
                '<p>Replacement data</p>'
                '<footer thing="bob">'
                    '<button name="action_next" type="object" string="New button"/>'
                '</footer>'
            '</form>')

    def test_view_inheritance_divergent_models(self):
        Views = self.registry('ir.ui.view')

        v1 = Views.create(self.cr, self.uid, {
            'name': "bob",
            'model': 'ir.ui.view.custom',
            'arch': """
                <form string="Base title" version="7.0">
                    <separator string="separator" colspan="4"/>
                    <footer>
                        <button name="action_next" type="object" string="Next button"/>
                        or
                        <button string="Skip" special="cancel" />
                    </footer>
                </form>
            """
        })
        v2 = Views.create(self.cr, self.uid, {
            'name': "edmund",
            'model': 'ir.ui.view',
            'inherit_id': v1,
            'arch': """
                <data>
                    <form position="attributes" version="7.0">
                        <attribute name="string">Replacement title</attribute>
                    </form>
                    <footer position="replace">
                        <footer>
                            <button name="action_next" type="object" string="New button"/>
                        </footer>
                    </footer>
                    <separator string="separator" position="replace">
                        <p>Replacement data</p>
                    </separator>
                </data>
            """
        })
        v3 = Views.create(self.cr, self.uid, {
            'name': 'jake',
            'model': 'ir.ui.menu',
            'inherit_id': v1,
            'priority': 17,
            'arch': """
                <footer position="attributes">
                    <attribute name="thing">bob</attribute>
                </footer>
            """
        })

        view = self.registry('ir.ui.view').fields_view_get(
            self.cr, self.uid, v2, view_type='form', context={
                # fucking what?
                'check_view_ids': [v2, v3]
            })
        self.assertEqual(view['type'], 'form')
        self.assertEqual(
            lxml.etree.tostring(lxml.etree.fromstring(
                view['arch'],
                parser=lxml.etree.XMLParser(remove_blank_text=True)
            )),
            '<form string="Replacement title" version="7.0">'
                '<p>Replacement data</p>'
                '<footer>'
                    '<button name="action_next" type="object" string="New button"/>'
                '</footer>'
            '</form>')

if __name__ == '__main__':
    unittest2.main()
