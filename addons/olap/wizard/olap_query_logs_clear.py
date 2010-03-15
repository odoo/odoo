##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from osv import fields, osv
from service import web_services
import pooler
import time
import wizard

class olap_query_logs_clear(osv.osv_memory):
    """ Clear the Logs for Given User  """
    _name = "olap.query.logs.clear"
    _description = "Olap Query Logs Clear"
    _columns = {
        'user_name':fields.char('User',size=64,required=True,readonly=True),
    }

    def _getdata(self,cr,uid,context={}):
        user = self.pool.get('res.users').browse(cr,uid,uid)
        return user.name

    _defaults = {
        'user_name': _getdata
            }

    def clear_logs(self,cr,uid,part,context={}):
        ids = self.pool.get('olap.query.logs').search(cr,uid,[('user_id','=',uid)])
        self.pool.get('olap.query.logs').unlink(cr, uid,ids,context)
        data_obj = self.pool.get('ir.model.data')
        id2 = data_obj._get_id(cr, uid, 'olap', 'view_olap_query_logs_clear_msg')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        value = {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'olap.query.logs.clear.msg',
            'views': [(id2,'form'),(False,'tree'),(False,'calendar'),(False,'graph')],
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
        return value

olap_query_logs_clear()

class olap_query_logs_clear_msg(osv.osv_memory):
    _name = "olap.query.logs.clear.msg"
    _description = "Olap Query Logs Clear Message"
    _columns = {

            }
olap_query_logs_clear_msg()
# vim: ts=4 sts=4 sw=4 si et
