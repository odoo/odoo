# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRl (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public license as
#    published by the Free Software Foundation, either version 3 of the
#    license, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABIlITY or FITNESS FOR A PARTICUlAR PURPOSE.  See the
#    GNU Affero General Public license for more details.
#
#    You should have received a copy of the GNU Affero General Public license
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools.translate import _

class document_page_make_index(osv.osv_memory):
    """ Create Index For Selected Page """

    _name = "document.page.make.index"
    _description = "Create Index"

    def document_page_do_index(self, cr, uid, ids, context=None):

        """ Makes Index according to page hierarchy
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: list of document page index’s IDs

        """
        if context is None:
            context = {}
        data = context and context.get('active_ids', []) or []
        print 'data',tuple(data)
        if not data:
            return {'type':  'ir.actions.act_window_close'}
        
        for index_obj in self.browse(cr, uid, ids, context=context):
            document_obj = self.pool.get('document.page')
            if not ids:
                return {}
            cr.execute('select id,index,parent_id from document_page where id in %s '\
                       'and type=%s' ,(tuple(data),'index',))
            lst_all = cr.fetchall()
            ls_p = []
            ls_np =[]
            s_ids = {}
            p_ids = {}
            for m in lst_all:
                if m[2] == None:
                    ls_np.append(m)
                    if m[1]:
                        s_ids[int(m[1])] = ls_np.index(m)+1
                        if s_ids:
                            document_obj.write(cr, uid, m[0], {'index':s_ids[int(m[1])]})
                if m[2]:
                    ls_p.append(m)
                    if m[1]:
                        dict = {}
                        for l in ls_p:
                            if l[2] not in dict:
                                dict[l[2]] = []
                                dict[l[2]].append(l)
                            else:
                                dict[l[2]].append(l)
                        
                        p_ids[m[1]] =  str(m[2]) + "." + str(dict[m[2]].index(m)+1)
                        if p_ids:
                            document_obj.write(cr, uid, m[0], {'index':p_ids[m[1]]})
                    
        return {'type':  'ir.actions.act_window_close'}

document_page_make_index()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
