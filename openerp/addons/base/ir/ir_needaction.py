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

class ir_needaction_users(osv.osv):
    '''
    ir_needaction_users holds data related to the needaction
    mechanism inside OpenERP. A needaction is characterized by:
    - res_model: model of the record requiring an action
    - res_id: ID of the record requiring an action
    - user_id: foreign key to the res.users table, to the user that
      has to perform the action
    '''
    
    _name = 'ir.needaction_users'
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
        if context is None:
            context = {}
        needact_ids = self.search(cr, uid, [('res_model', '=', res_model), ('res_id', 'in', res_ids)], context=context)
        return map(itemgetter('res_id'), self.read(cr, uid, needact_ids, context=context))
    
    def create_users(self, cr, uid, res_ids, res_model, user_ids, context=None):
        """Given res_ids of res_model, add user_ids to the relationship table"""
        if context is None:
            context = {}
        for res_id in res_ids:
            for user_id in user_ids:
                self.create(cr, uid, {'res_model': res_model, 'res_id': res_id, 'user_id': user_id}, context=context)
        return True
    
    def unlink_users(self, cr, uid, res_ids, res_model, context=None):
        """Given res_ids of res_model, delete all entries in the relationship table"""
        if context is None:
            context = {}
        to_del_ids = self.search(cr, uid, [('res_model', '=', res_model), ('res_id', 'in', res_ids)], context=context)
        return self.unlink(cr, uid, to_del_ids, context=context)
    
    def update_users(self, cr, uid, res_ids, res_model, user_ids, context=None):
        """Given res_ids of res_model, update their entries in the relationship table to user_ids"""
        # read current records
        cur_users = self._get_users(cr, uid, res_ids, res_model, context=context)
        if len(cur_users) == len(user_ids) and all([cur_user in user_ids for cur_user in cur_users]):
            return True
        # unlink old records
        self.unlink_users(cr, uid, res_ids, res_model, context=context)
        # link new records
        self.create_users(cr, uid, res_ids, res_model, user_ids, context=context)
        return True


class ir_needaction_mixin(osv.osv):
    '''Mixin class for objects using the need action feature.
    
    Need action feature can be used by objects willing to be able to
    signal that an action is required on a particular record. If in the
    business logic an action must be performed by somebody, for instance
    validation by a manager, this mechanism allows to set a list of
    users asked to perform an action.
    
    This class wraps a class (ir.needaction_users) that behaves
    like a many2many field. However, no field is added to the model
    inheriting from base.needaction. The mixin class manages the low-level
    considerations of updating relationships. Every change made on the
    record calls a method that updates the relationships.
    
    Objects using the need_action feature should override the
    ``get_needaction_user_ids`` method. This methods returns a dictionary
    whose keys are record ids, and values a list of user ids, like
    in a many2many relationship. Therefore by defining only one method,
    you can specify if an action is required by defining the users
    that have to do it, in every possible situation.
    
    This class also offers several global services,:
    - ``needaction_get_record_ids``: for the current model and uid, get
      all record ids that ask this user to perform an action. This
      mechanism is used for instance to display the number of pending
      actions in menus, such as Leads (12)
    - ``needaction_get_action_count``: as ``needaction_get_record_ids``
      but returns only the number of action, not the ids (performs a
      search with count=True)
    - ``needaction_get_user_record_references``: for a given uid, get all
      the records that ask this user to perform an action. Records
      are given as references, a list of tuples (model_name, record_id)
    '''
    _name = 'ir.needaction_mixin'
    _description = 'Need action of users on records API'
    
    #------------------------------------------------------
    # Addon API
    #------------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        """ Returns the user_ids that have to perform an action
            :return: dict { record_id: [user_ids], }
        """
        return dict.fromkeys(ids, [])
    
    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        needact_table_obj = self.pool.get('ir.needaction_users')
        # perform create
        obj_id = super(ir_needaction, self).create(cr, uid, values, context=context)
        # link user_ids
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, [obj_id], context=context)
        needact_table_obj.create_users(cr, uid, [obj_id], self._name, needaction_user_ids[obj_id], context=context)
        return obj_id
    
    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        needact_table_obj = self.pool.get('ir.needaction_users')
        # perform write
        write_res = super(ir_needaction, self).write(cr, uid, ids, values, context=context)
        # get and update user_ids
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, ids, context=context)
        for id in ids:
            needact_table_obj.update_users(cr, uid, [id], self._name, needaction_user_ids[id], context=context)
        return write_res
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # unlink user_ids
        needact_table_obj = self.pool.get('ir.needaction_users')
        needact_table_obj.unlink_users(cr, uid, ids, self._name, context=context)
        # perform unlink
        return super(ir_needaction, self).unlink(cr, uid, ids, context=context)
    
    #------------------------------------------------------
    # Need action API
    #------------------------------------------------------
    
    def needaction_get_record_ids(self, cr, uid, user_id, limit=80, context=None):
        """Given the current model and a user_id
           get the number of actions it has to perform"""
        if context is None:
            context = {}
        needact_table_obj = self.pool.get('ir.needaction_users')
        needact_table_ids = needact_table_obj.search(cr, uid, [('res_model', '=', self._name), ('user_id', '=', user_id)], limit=limit, context=context)
        return map(itemgetter('res_id'), needact_table_obj.read(cr, uid, needact_table_ids, context=context))
    
    def needaction_get_action_count(self, cr, uid, user_id, limit=80, context=None):
        """Given the current model and a user_id
           get the number of actions it has to perform"""
        if context is None:
            context = {}
        needact_table_obj = self.pool.get('ir.needaction_users')
        return needact_table_obj.search(cr, uid, [('res_model', '=', self._name), ('user_id', '=', user_id)], limit=limit, count=True, context=context)
    
    def needaction_get_record_references(self, cr, uid, user_id, offset=None, limit=None, order=None, context=None):
        """For a given user_id, get all the records that asks this user to
           perform an action. Records are given as references, a list of
           tuples (model_name, record_id).
           This method is trans-model."""
        if context is None:
            context = {}
        needact_table_obj = self.pool.get('ir.needaction_users')
        needact_table_ids = needact_table_obj.search(cr, uid, [('user_id', '=', user_id)], offset=offset, limit=limit, order=order, context=context)
        needact_records = needact_table_obj.read(cr, uid, needact_table_ids, context=context)
        return map(itemgetter('res_model', 'id'), needact_records)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
