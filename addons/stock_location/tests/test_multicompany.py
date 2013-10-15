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
        self.stock_warehouse = self.registry('stock.warehouse')

        model, group_user_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        model, group_stock_manager_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'stock', 'group_stock_manager')
        model, company_2_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'stock', 'res_company_2')
        self.company_2_id = company_2_id
        self.multicompany_user_id = self.res_users.create(cr, uid,
            {'name': 'multicomp', 'login': 'multicomp',
             'groups_id': [(6, 0, [group_user_id, group_stock_manager_id])],
             'company_id': company_2_id, 'company_ids': [(6,0,[company_2_id])]})

    def test_00_multicompany_default_stock_move(self):
        """check no error on getting default stock.move values in multicompany setting"""
        cr, uid, context = self.cr, self.multicompany_user_id, {}
        fields = ['location_id', 'location_dest_id']
        
        new_warehouse_id = self.registry('stock.warehouse').create(cr, uid, {'name':'DemoWH_MultiComp','reception_steps':'three_steps', 'delivery_steps' : 'pick_pack_ship', 'company_id':self.company_2_id,'code':'dmwh'}, context=context)
        warehouse = self.registry('stock.warehouse').browse(cr, uid, new_warehouse_id, context=context)
        
        for type in ('in', 'int', 'out'):
            
            type_id = warehouse[type + '_type_id'].id
            context['default_picking_type_id'] = type_id            
            defaults = self.stock_move.default_get(cr, uid, ['location_id', 'location_dest_id','picking_type_id'], context=context)
            if defaults and defaults['picking_type_id']:
                def_type = self.registry('stock.picking.type').browse(cr,uid,defaults['picking_type_id'],context).code_id
            else:
                assert False, "Picking type undefined "
           
            for field in fields:
                                                
                if defaults.get(field):
                    try:
                        print("try : ",defaults[field])                                      
                        self.stock_location.check_access_rule(cr, uid, [defaults[field]], 'read', context)
                    except Exception, exc:
                        print("catch : ",defaults[field])                        
                        assert False, "unreadable location %s: %s" % (field, exc)
                    
            self.assertEqual(def_type[0:len(type)].lower(), type, "wrong move type")
