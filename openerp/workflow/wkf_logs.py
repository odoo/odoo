# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

#
# May be uncommented to logs workflows modifications
#
import openerp.netsvc as netsvc

def log(cr,ident,act_id,info=''):
    return 
    #    msg = """
    #res_type: %r
    #res_id: %d
    #uid: %d
    #act_id: %d
    #info: %s
    #""" % (ident[1], ident[2], ident[0], act_id, info)

    #cr.execute('insert into wkf_logs (res_type, res_id, uid, act_id, time, info) values (%s,%s,%s,%s,current_time,%s)', (ident[1],int(ident[2]),int(ident[0]),int(act_id),info))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

