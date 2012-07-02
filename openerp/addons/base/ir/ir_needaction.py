# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import openerp.pooler as pooler
from operator import itemgetter
from osv import osv, fields
from tools.translate import _

class ir_needaction_users_rel(osv.Model):
    ''' ir_needaction_users_rel holds data related to the needaction 
    mechanism inside OpenERP. A row in this model is characterized 
    by:
    - res_model: model of the record requiring an action
    - res_id: ID of the record requiring an action
    - user_id: foreign key to the res.users table, to the user that has to
      perform the action
    This model can be seen as a many2many, linking (res_model, res_id) to users
    (those whose attention is required on the record). '''
    
    _name = 'ir.needaction_users_rel'
    _description = 'Needaction relationship table'
    _rec_name = 'id'
    _order = 'id desc'
    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        select=1, required=True),
        'res_id': fields.integer('Related Document ID',
                        select=1, required=True),
        'user_id': fields.many2one('res.users', string='Related User',
                        ondelete='cascade', select=1, required=True),
    }
    
    def _get_users(self, cr, uid, res_ids, res_model, context=None):
        """Given res_ids of res_model, get user_ids present in table"""
        rel_ids = self.search(cr, uid, [('res_model', '=', res_model), ('res_id', 'in', res_ids)], context=context)
        return list(set(map(itemgetter('user_id'), self.read(cr, uid, rel_ids, ['user_id'], context=context))))
    
    def create_users(self, cr, uid, res_ids, res_model, user_ids, context=None):
        """Given res_ids of res_model, add user_ids to the relationship table"""
        for res_id in res_ids:
            for user_id in user_ids:
                self.create(cr, uid, {'res_model': res_model, 'res_id': res_id, 'user_id': user_id}, context=context)
        return True
    
    def unlink_users(self, cr, uid, res_ids, res_model, context=None):
        """Given res_ids of res_model, delete all entries in the relationship table"""
        to_del_ids = self.search(cr, uid, [('res_model', '=', res_model), ('res_id', 'in', res_ids)], context=context)
        return self.unlink(cr, uid, to_del_ids, context=context)
    
    def update_users(self, cr, uid, res_ids, res_model, user_ids, context=None):
        """Given res_ids of res_model, update their entries in the relationship table to user_ids"""
        # read current records
        cur_users = self._get_users(cr, uid, res_ids, res_model, context=context)
        if len(cur_users) == len(user_ids) and all(cur_user in user_ids for cur_user in cur_users):
            return True
        # unlink old records
        self.unlink_users(cr, uid, res_ids, res_model, context=context)
        # link new records
        self.create_users(cr, uid, res_ids, res_model, user_ids, context=context)
        return True


class ir_needaction_mixin(osv.Model):
    '''Mixin class for objects using the need action feature.
    
    Need action feature can be used by objects having to be able to 
    signal that an action is required on a particular record. If in 
    the business logic an action must be performed by somebody, for 
    instance validation by a manager, this mechanism allows to set a 
    list of users asked to perform an action.
    
    This class wraps a class (ir.ir_needaction_users_rel) that 
    behaves like a many2many field. This class handles the low-level 
    considerations of updating relationships. Every change made on 
    the record calls a method that updates the relationships.
    
    Objects using the 'need_action' feature should override the 
    ``get_needaction_user_ids`` method. This methods returns a 
    dictionary whose keys are record ids, and values a list of user 
    ids, like in a many2many relationship. Therefore by defining 
    only one method, you can specify if an action is required by 
    defining the users that have to do it, in every possible 
    situation.
    
    This class also offers several global services: 
    - ``needaction_get_record_ids``: for the current model and uid, get
    all record ids that ask this user to perform an action. This 
    mechanism is used for instance to display the number of pending 
    actions in menus, such as Leads (12)
    - ``needaction_get_action_count``: as ``needaction_get_record_ids``
    but returns only the number of action, not the ids (performs a 
    search with count=True)

    The ``ir_needaction_mixin`` class adds a calculated field 
    ``needaction_pending``. This function field allows to state 
    whether a given record has a needaction for the current user. 
    This is usefull if you want to customize views according to the 
    needaction feature. For example, you may want to set records in 
    bold in a list view if the current user has an action to perform 
    on the record. '''
    
    _name = 'ir.needaction_mixin'
    _description = 'Need action mixin'
    
    def get_needaction_pending(self, cr, uid, ids, name, arg, context=None):
        res = {}
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, ids, context=context)
        for id in ids:
            res[id] = uid in needaction_user_ids[id]
        return res

    def search_needaction_pending(self, cr, uid, self_again, field_name, criterion, context=None):
        ids = self.needaction_get_record_ids(
            cr, uid, uid, limit=1024, context=context)
        return [('id', 'in', ids)]
    
    _columns = {
        'needaction_pending': fields.function(
            get_needaction_pending, type='boolean',
            fnct_search=search_needaction_pending,
            string='Need action pending',
            help="If True, this field states that users have to perform an " \
                 "action This field comes from the ir.needaction_mixin class."),
    }
    
    #------------------------------------------------------
    # Addon API
    #------------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        """ Returns the user_ids that have to perform an action
            :return: dict { record_id: [user_ids], }
        """
        return dict((id,list()) for id in ids)
    
    def create(self, cr, uid, values, context=None):
        rel_obj = self.pool.get('ir.needaction_users_rel')
        # perform create
        obj_id = super(ir_needaction_mixin, self).create(cr, uid, values, context=context)
        # link user_ids
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, [obj_id], context=context)
        rel_obj.create_users(cr, uid, [obj_id], self._name, needaction_user_ids[obj_id], context=context)
        return obj_id
    
    def write(self, cr, uid, ids, values, context=None):
        rel_obj = self.pool.get('ir.needaction_users_rel')
        # perform write
        write_res = super(ir_needaction_mixin, self).write(cr, uid, ids, values, context=context)
        # get and update user_ids
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, ids, context=context)
        for id in ids:
            rel_obj.update_users(cr, uid, [id], self._name, needaction_user_ids[id], context=context)
        return write_res
    
    def unlink(self, cr, uid, ids, context=None):
        # unlink user_ids
        rel_obj = self.pool.get('ir.needaction_users_rel')
        rel_obj.unlink_users(cr, uid, ids, self._name, context=context)
        # perform unlink
        return super(ir_needaction_mixin, self).unlink(cr, uid, ids, context=context)
    
    #------------------------------------------------------
    # "Need action" API
    #------------------------------------------------------
    
    def needaction_get_record_ids(self, cr, uid, user_id, limit=80, context=None):
        """Given the current model and a user_id
           return the record ids that require the user to perform an
           action"""
        rel_obj = self.pool.get('ir.needaction_users_rel')
        rel_ids = rel_obj.search(cr, uid, [('res_model', '=', self._name), ('user_id', '=', user_id)], limit=limit, context=context)
        return map(itemgetter('res_id'), rel_obj.read(cr, uid, rel_ids, ['res_id'], context=context))
    
    def needaction_get_action_count(self, cr, uid, user_id, limit=80, context=None):
        """Given the current model and a user_id
           get the number of actions it has to perform"""
        rel_obj = self.pool.get('ir.needaction_users_rel')
        return rel_obj.search(cr, uid, [('res_model', '=', self._name), ('user_id', '=', user_id)], limit=limit, count=True, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
