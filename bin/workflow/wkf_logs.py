# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#
# May be uncommented to logs workflows modifications
#

def log(cr,ident,act_id,info=''):
    pass
    #cr.execute('insert into wkf_logs (res_type, res_id, uid, act_id, time, info) values (%s,%d,%d,%d,current_time,%s)', (ident[1],int(ident[2]),int(ident[0]),int(act_id),info))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

