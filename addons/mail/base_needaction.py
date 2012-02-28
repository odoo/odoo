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
import tools
import logging
from osv import osv, fields
from tools.translate import _

class mail_needaction(osv.osv):
    '''TODO
    '''
    _name = 'mail.needaction'
    _description = 'Need action Engine'
    
    def get_needaction_user_id(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = False
        return result
    
    #def set_needaction_user_id(self, cr, uid, id, name, value, arg, context=None):
        #"""
        #@param name: Name of field
        #@param value: Value of field
        #@param arg: User defined argument
        #"""
        #if context is None:
            #context = {}
        #return self.write(cr, uid, [id], {name: value}, context=context)

    def get_needaction_user_id_wrapper(self, cr, uid, ids, name, arg, context=None):
        return self.get_needaction_user_id(cr, uid, ids, name, arg, context=context)
    
    def set_needaction_user_id_wrapper(self, cr, uid, id, name, value, arg, context=None):
        return self.set_needaction_user_id(cr, uid, id, name, value, arg, context=context)

    _columns = {
        'need_action': fields.boolean('Need action'),
        'need_action_user_id': fields.function(get_needaction_user_id_wrapper,
                        #fnct_inv=set_needaction_user_id_wrapper,
                        type='many2one', relation='res.users', store=True, string='User'),
                        
    }
    
    _defaults = {
        'need_action': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
