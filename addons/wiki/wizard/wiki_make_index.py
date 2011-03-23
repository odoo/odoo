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
import re

class wiki_make_index(osv.osv_memory):
    """ Create Index For Selected Page """

    _name = "wiki.make.index"
    _description = "Create Index"

    def wiki_do_index(self, cr, uid, ids, context=None):

        """ Makes Index according to page hierarchy
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: list of wiki index’s IDs

        """
        if context is None:
            context = {}
        data = context and context.get('active_ids', []) or []
        
        if not data:
            return {'type':  'ir.actions.act_window_close'}
        
        for index_obj in self.browse(cr, uid, ids, context=context):
            wiki_pool = self.pool.get('wiki.wiki')
            cr.execute("Select id, section from wiki_wiki where id IN %s \
                            order by section ", (tuple(data),))
            lst0 = cr.fetchall()
            if not lst0[0][1]:
                raise osv.except_osv(_('Warning !'), _('There is no section in this Page'))

            for i in lst0[0][1]:
                match = re.match('[0-9\.]', i)
                if not match:
                    raise osv.except_osv(_('Warning !'), _('The section values must be like 1/1.1/1.3.4'))
            lst = []
            s_ids = {}

            for l in lst0:
                s_ids[l[1]] = l[0]
                lst.append(l[1])

            lst.sort()
            val = None
            def toint(x):
                try:
                    return int(x)
                except:
                    return 1

            lst = map(lambda x: map(toint, x.split('.')), lst)

            result = []
            current = ['0']
            current2 = []

            for l in lst:
                for pos in range(len(l)):
                    if pos >= len(current):
                        current.append('1')
                        continue
                    if (pos == len(l) - 1) or (pos >= len(current2)) or (toint(l[pos]) > toint(current2[pos])):
                        current[pos] = str(toint(current[pos]) + 1)
                        current = current[:pos + 1]
                        if pos == len(l) - 1:
                            break
                key = ('.'.join([str(x) for x in l]))
                id = s_ids[key]
                val = ('.'.join([str(x) for x in current[:]]), id)

            if val:
                result.append(val)
            current2 = l

            for rs in result:
                wiki_pool.write(cr, uid, [rs[1]], {'section':rs[0]})

        return {'type':  'ir.actions.act_window_close'}

wiki_make_index()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
