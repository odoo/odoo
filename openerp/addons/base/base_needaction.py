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

from osv import osv, fields
from tools.translate import _

class base_needaction_users_rel(osv.osv):
    '''
    base_needaction_users_rel holds the data related to the needaction
    mechanism inside OpenERP. A needaction is characterized by:
    - res_model: model of the followed objects
    - res_id: ID of resource
    - user_id: foreign key to the res.users table, to the user that
      has to perform an action
    '''
    
    _name = 'base.needaction_users_rel'
    _rec_name = 'id'
    _order = 'res_model asc'
    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        select=1, required=True),
        'res_id': fields.integer('Related Document ID',
                        select=1, required=True),
        'user_id': fields.many2one('res.users', string='Related User ID',
                        ondelete='cascade', select=1, required=True),
    }


class base_needaction(osv.osv):
    '''Mixin class for object implementing the need action mechanism.
    
    Need action mechanism can be used by objects that have to be able to
    signal that an action is required on a particular record. If in the
    business logic an action must be performed by somebody, for instance
    validation by a manager, this mechanism allows to set a field with
    the user_id of the user requested to perform the action.
    
    Technically, this class adds a need_action_user_id field; when
    set to false, no action is required; when an user_id is set,
    this user has an action to perform. This field is a function field.
    Setting an user_id is done through redefining the get_needaction_user_id method.
    Therefore by redefining only one method, you can specify
    the cases in which an action will be required on a particular record.
    
    This mechanism is used for instance to display the number of pending actions
    in menus, such as Leads (12).
    '''
    _name = 'base.needaction'
    _description = 'Need action mechanism'
    
    _columns = {
    }
    
    #------------------------------------------------------
    # need action relationship management
    #------------------------------------------------------
    
    def _link_users(self, cr, uid, ids, user_ids, context=None):
        if context is None:
            context = {}
        needact_rel_obj = self.pool.get('base.needaction_users_rel')
        for id in ids:
            for user_id in user_ids:
                needact_rel_obj.create(cr, uid, {'res_model': self._name, 'res_id': id, 'user_id': user_id}, context=context)
        return True
    
    def _unlink_users(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        needact_rel_obj = self.pool.get('base.needaction_users_rel')
        to_del_ids = needact_rel_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', 'in', ids)], context=context)
        return needact_rel_obj.unlink(cr, uid, to_del_ids, context=context)
    
    def _update_users(self, cr, uid, ids, user_ids, context=None):
        if context is None:
            context = {}
        # unlink old records
        self._unlink_users(cr, uid, ids, context=context)
        # link new records
        for res_id in ids:
            self._link_users(cr, uid, ids, user_ids, context=context)
        return True
    
    #------------------------------------------------------
    # Addon API
    #------------------------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, [])
        return result
    
    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        # perform create
        obj_id = super(base_needaction, self).create(cr, uid, ids, values, context=context)
        # link user_ids
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, [obj_id], context=context)
        self._update_users(cr, uid, [id], needaction_user_ids[obj_id], context=context)
        return obj_id
    
    def write(self, cr, uid, ids, values, context=None):
        if context is None:
            context = {}
        # get and update user_ids
        needaction_user_ids = self.get_needaction_user_ids(cr, uid, ids, context=context)
        for id in ids:
            self._update_users(cr, uid, [id], needaction_user_ids[id], context=context)
        # perform write
        return super(base_needaction, self).write(cr, uid, ids, values, context=context)
    
    def unlink(self, cr, uids, ids, context=None):
        if context is None:
            context = {}
        # unlink user_ids
        self._unlink_users(cr, uid, ids, context=context)
        # perform unlink
        return super(base_needaction, self).unlink(cr, uid, ids, values, context=context)
    
    #------------------------------------------------------
    # General API
    #------------------------------------------------------
    
    def needaction_get_user_needaction_ids(self, cr, uid, user_id, offset=0, limit=None, order=None, count=False, context=None):
        if context is None:
            context = {}
        needact_rel_obj = self.pool.get('base.needaction_users_rel')
        search_res = needact_rel_obj.search(cr, uid, [('user_id', '=', user_id)], offset=offset, limit=limit, order=order, count=count, context=context)
        return search_res
    
    def needaction_get_record_references(self, cr, uid, user_id, offset=0, limit=None, order=None, context=None):
        if context is None:
            context = {}
        needact_rel_obj = self.pool.get('base.needaction_users_rel')
        needact_obj_ids = self.get_user_needaction_ids(cr, uid, user_id, offset=offset, limit=limit, order=order, context=context)
        needact_objs = needact_rel_obj.browse(cr, uid, needact_obj_ids, context=context)
        record_references = [(needact_obj.res_model, needact_obj.res_id) for needact_obj in needact_objs]
        return record_references


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
