# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv


class ir_exports(osv.osv):
    _name = "ir.exports"
    _order = 'name'
    _columns = {
        'name': fields.char('Export Name'),
        'resource': fields.char('Resource', select=True),
        'export_fields': fields.one2many('ir.exports.line', 'export_id',
                                         'Export ID', copy=True),
    }


class ir_exports_line(osv.osv):
    _name = 'ir.exports.line'
    _order = 'id'
    _columns = {
        'name': fields.char('Field Name'),
        'export_id': fields.many2one('ir.exports', 'Export', select=True, ondelete='cascade'),
    }
