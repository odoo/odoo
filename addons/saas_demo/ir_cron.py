# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>).
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

from osv import osv

class ir_cron(osv.osv):
    """ extend ir.cron to make sure all cron jobs are inactive
    """
    _inherit = 'ir.cron'

    def create(self, cr, uid, vals, context=None):
        vals['active'] = False
        return super(ir_cron, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals['active'] = False
        return super(ir_cron, self).write(cr, uid, ids, vals, context=context)

    def deactivate_all(self, cr, uid, context=None):
        ids = self.search(cr, uid, [], context=context)
        return self.write(cr, uid, ids, {'active': False}, context=context)
