# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from openerp.osv import osv, fields
from openerp.tools.translate import _

class ir_logging(osv.Model):
    _name = 'ir.logging'
    _order = 'id DESC'

    EXCEPTIONS_TYPE = [
        ('client', 'Client'),
        ('server', 'Server')
    ]

    _columns = {
        'create_date': fields.datetime('Create Date', readonly=True),
        'create_uid': fields.integer('Uid', readonly=True),  # Integer not m2o is intentionnal
        'name': fields.char('Name', required=True),
        'type': fields.selection(EXCEPTIONS_TYPE, string='Type', required=True, select=True),
        'dbname': fields.char('Database Name', select=True),
        'level': fields.char('Level', select=True),
        'message': fields.text('Message', required=True),
        'path': fields.char('Path', required=True),
        'func': fields.char('Function', required=True),
        'line': fields.char('Line', required=True),
    }
