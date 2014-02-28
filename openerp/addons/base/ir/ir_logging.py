##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<http://www.openerp.com>)
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
import logging

from openerp.osv import osv, fields
from openerp.tools.translate import _

class ir_logging(osv.Model):
    _name = 'ir.logging'

    EXCEPTIONS_TYPE = [
        ('client', 'Client'),
        ('server', 'Server')
    ]

    _columns = {
        'name': fields.char('Name', required=True),
        'type': fields.selection(EXCEPTIONS_TYPE, string='Type', required=True, select=True),
        'dbname': fields.char('Database Name'),
        'level': fields.char('Level'),
        'message': fields.text('Message', required=True),
        'exception': fields.text('Exception'),
        'path': fields.char('Path', required=True),
        'func': fields.char('Function', required=True),
        'line': fields.char('Line', required=True),
    }

    def call_function(self, cr, uid, ids, context=None):
        logger = logging.getLogger()
        logger.error("I think there is an error")
        try:
            raise Exception("I want to kill your process...")
        except Exception, ex:
            logger.exception("Please log me into the database")
        return True