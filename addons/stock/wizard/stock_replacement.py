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

from osv import fields, osv
from tools.translate import _
import time

class stock_replacement(osv.osv_memory):
    """
        This class has been defined for replacement wizard
    """
    _name = "stock.replacement"
    _description = "Stock Replacement"

    def get_composant(self, cr, uid, ids, context=None):
        return {}

    def replace_composant(self, cr, uid, ids, context=None):
        """ To open a new wizard that acknowledge, a replacement task
        @return: It returns the replacement acknowledgement form
        """
        return {
            'name': False,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.replacement.result',
            'type': 'ir.actions.act_window',
            'target':'new',
        }

stock_replacement()

class stock_replacement_result(osv.osv_memory):
    """
        This class has been defined for replacement result
    """
    _name = "stock.replacement.result"
    _description = "Stock Replacement result"

stock_replacement_result()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

