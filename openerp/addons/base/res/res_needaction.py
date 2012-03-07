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

import time
from osv import osv, fields
from tools.translate import _

class res_needaction(osv.osv):
    '''Mixin class for object implementing a need_action mechanism
    
    Need action mechanism can be used by objects wanting to be able to
    signal that an action is required on a particular record. If in the
    business logic an action must be performed by somebody, for instance
    validation by a manager, this mechanism allows to add have a field
    linking to the user requested to perform the action.
    
    Technically, this class adds a need_action_user_id field; when
    set to false, no action is required; when an user_id is set,
    this user has an action to perform. Setting an user_id is done
    through redefining the get_needaction_user_id method, that
    stores the need_action_user_id function fields.
    
    This mechanism is used for instance to display the number of pending action
    in menus.
    '''
    _name = 'res.needaction'
    _description = 'Need action Engine'
    
    def get_needaction_user_id(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = False
        return result

    ''' Wrapper: in 6.1 the reference to a method is given to a function
    field, not the function name. Inheritance is therefore not directly
    possible.'''
    def get_needaction_user_id_wrapper(self, cr, uid, ids, name, arg, context=None):
        return self.get_needaction_user_id(cr, uid, ids, name, arg, context=context)

    _columns = {
        'need_action_user_id': fields.function(get_needaction_user_id_wrapper,
                        type='many2one', relation='res.users', store=True,
                        select=1, string='User'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
