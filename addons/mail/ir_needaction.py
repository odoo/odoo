# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
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

from osv import osv

class ir_needaction_mixin(osv.Model):
    """ Update of ir.needaction_mixin class
        - override the get_needaction_user_ids method to define the default
          mail gateway need_action: when the object is unread, the object
          responsible has an action to perform.
    """
    _name = 'ir.needaction_mixin'
    _inherit = ['ir.needaction_mixin']
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        """ Returns the user_ids that have to perform an action. It the
            document mail state is unread (False), return object.user_id.id
            as need_action uid.
            :return: dict { record_id: [user_ids], }
        """
        result = super(ir_needaction_mixin, self).get_needaction_user_ids(cr, uid, ids, context=context)
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.message_state == False and obj.user_id:
                result[obj.id].append(obj.user_id.id)
        return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
