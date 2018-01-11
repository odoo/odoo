# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class showdiff(osv.osv_memory):
    """ Disp[ay Difference for History """

    _name = 'blog.post.history.show_diff'

    def get_diff(self, cr, uid, context=None):
        if context is None:
            context = {}
        history = self.pool.get('blog.post.history')
        ids = context.get('active_ids', [])

        diff = ""
        if len(ids) == 2:
            if ids[0] > ids[1]:
                diff = history.getDiff(cr, uid, ids[1], ids[0])
            else:
                diff = history.getDiff(cr, uid, ids[0], ids[1])

        elif len(ids) == 1:
            old = history.browse(cr, uid, ids[0])
            nids = history.search(cr, uid, [('post_id', '=', old.post_id.id)])
            nids.sort()
            diff = history.getDiff(cr, uid, ids[0], nids[-1])
        else:
            raise osv.except_osv(_('Warning!'), _('You need to select minimum one or maximum two history revisions!'))
        return diff

    _columns = {
        'diff': fields.text('Diff', readonly=True),
    }

    _defaults = {
        'diff': get_diff
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
