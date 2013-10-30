# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tests import common


class TestStockMulticompany(common.TransactionCase):

    def setUp(self):
        super(TestStockMulticompany, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_model_data = self.registry('ir.model.data')
        self.res_users = self.registry('res.users')
        self.stock_location = self.registry('stock.location')
        self.stock_move = self.registry('stock.move')
        self.stock_fill_inventory = self.registry('stock.fill.inventory')
        self.stock_warehouse = self.registry('stock.warehouse')

        model, group_user_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        model, group_stock_manager_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'stock', 'group_stock_manager')
        model, company_2_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'stock', 'res_company_2')
        self.multicompany_user_id = self.res_users.create(cr, uid,
            {'name': 'multicomp', 'login': 'multicomp',
             'groups_id': [(6, 0, [group_user_id, group_stock_manager_id])],
             'company_id': company_2_id, 'company_ids': [(6,0,[company_2_id])]})

    def test_00_multicompany_default_stock_move(self):
        """check no error on getting default stock.move values in multicompany setting"""
        cr, uid, context = self.cr, self.multicompany_user_id, {}
        fields = ['location_id', 'location_dest_id']
        for type in ('in', 'internal', 'out'):
            context['picking_type'] = type
            defaults = self.stock_move.default_get(cr, uid, ['location_id', 'location_dest_id', 'type'], context)
            for field in fields:
                if defaults.get(field):
                    try:
                        self.stock_location.check_access_rule(cr, uid, [defaults[field]], 'read', context)
                    except Exception, exc:
                        assert False, "unreadable location %s: %s" % (field, exc)
            self.assertEqual(defaults['type'], type, "wrong move type")


    def test_10_multicompany_onchange_move_type(self):
        """check onchange_move_type does not return unreadable in multicompany setting"""
        cr, uid, context = self.cr, self.multicompany_user_id, {}
        fields = ['location_id', 'location_dest_id']
        for type in ('in', 'internal', 'out'):
            result = self.stock_move.onchange_move_type(cr, uid, [], type, context)['value']
            for field in fields:
                if result.get(field):
                    try:
                        self.stock_location.check_access_rule(cr, uid, [result[field]], 'read', context)
                    except Exception, exc:
                        assert False, "unreadable location %s: %s" % (field, exc)


    def test_20_multicompany_default_stock_fill_inventory(self):
        """check default location readability for stock_fill_inventory in multicompany setting"""
        cr, uid, context = self.cr, self.multicompany_user_id, {}
        defaults = self.stock_fill_inventory.default_get(cr, uid, ['location_id'], context)
        if defaults.get('location_id'):
            try:
                self.stock_location.check_access_rule(cr, uid, [defaults['location_id']], 'read', context)
            except Exception, exc:
                assert False, "unreadable source location: %s" % exc


    def test_30_multicompany_default_warehouse_location(self):
        """check default locations for warehouse in multicompany setting"""
        cr, uid, context = self.cr, self.multicompany_user_id, {}
        fields = ['lot_input_id', 'lot_stock_id', 'lot_output_id']
        defaults = self.stock_warehouse.default_get(cr, uid, fields, context)
        for field in fields:
            if defaults.get(field):
                try:
                    self.stock_location.check_access_rule(cr, uid, [defaults[field]], 'read', context)
                except Exception, exc:
                    assert False, "unreadable default %s: %s" % (field, exc)
