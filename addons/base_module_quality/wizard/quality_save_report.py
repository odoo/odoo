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

import base64
import cStringIO

from osv import osv
from tools.translate import _
from osv import osv, fields

class quality_save_report(osv.osv_memory):

    _name = "save.report"
    _description = "Save Report of Quality"

    def default_get(self, cr, uid, fields, context=None):
        res = super(quality_save_report, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids')
        data = self.pool.get('module.quality.detail').browse(cr, uid, active_ids, context=context)[0]
        if not data.detail:
            raise osv.except_osv(_('Warning'), _('No report to save!'))
        buf = cStringIO.StringIO(data.detail)
        out = base64.encodestring(buf.getvalue())
        buf.close()
        return {'module_file': out, 'name': data.name + '.html'}

    _columns = {
        'name': fields.char('File Name', required=True, size=32, help="Save report as .html format"),
        'module_file': fields.binary('Save report', required=True),
    }

quality_save_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: