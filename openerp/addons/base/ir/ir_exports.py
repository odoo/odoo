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

from openerp.osv import fields,osv


class ir_exports(osv.osv):
    _name = "ir.exports"
    _order = 'name'
    _columns = {
        'name': fields.char('Export Name', size=128),
        'resource': fields.char('Resource', size=128, select=True),
        'export_fields': fields.one2many('ir.exports.line', 'export_id',
                                         'Export ID'),
    }
ir_exports()


class ir_exports_line(osv.osv):
    _name = 'ir.exports.line'
    _order = 'id'
    _columns = {
        'name': fields.char('Field Name', size=64),
        'export_id': fields.many2one('ir.exports', 'Export', select=True, ondelete='cascade'),
    }
ir_exports_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

