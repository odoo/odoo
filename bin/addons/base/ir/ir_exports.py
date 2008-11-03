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

from osv import fields,osv


class ir_exports(osv.osv):
    _name = "ir.exports"
    _columns = {
        'name': fields.char('Export name', size=128),
        'resource': fields.char('Resource', size=128),
        'export_fields': fields.one2many('ir.exports.line', 'export_id',
                                         'Export Id'),
    }
ir_exports()


class ir_exports_line(osv.osv):
    _name = 'ir.exports.line'
    _columns = {
        'name': fields.char('Field name', size=64),
        'export_id': fields.many2one('ir.exports', 'Exportation', select=True, ondelete='cascade'),
    }
ir_exports_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

