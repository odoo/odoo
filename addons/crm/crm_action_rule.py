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

import re
import tools

from tools.translate import _
from tools import ustr
from osv import fields
from osv import osv

import crm

class base_action_rule(osv.osv):
    """ Base Action Rule """
    _inherit = 'base.action.rule'
    _description = 'Action Rules'

    _columns = {
        'act_section_id': fields.many2one('crm.case.section', 'Set Team to'),
        'act_categ_id': fields.many2one('crm.case.categ', 'Set Category to'),
    }

    def do_action(self, cr, uid, action, obj, context=None):
        res = super(base_action_rule, self).do_action(cr, uid, action, obj, context=context)
        model_obj = self.pool.get(action.model_id.model)
        write = {}
        if hasattr(action, 'act_section_id') and action.act_section_id:
            write['section_id'] = action.act_section_id.id

        if hasattr(action, 'act_categ_id') and action.act_categ_id:
            write['categ_ids'] = [(4, action.act_categ_id.id)]

        model_obj.write(cr, uid, [obj.id], write, context)
        return res

    def state_get(self, cr, uid, context=None):
        """Gets available states for crm"""
        res = super(base_action_rule, self).state_get(cr, uid, context=context)
        return res + crm.AVAILABLE_STATES

    def priority_get(self, cr, uid, context=None):
        res = super(base_action_rule, self).priority_get(cr, uid, context=context)
        return res + crm.AVAILABLE_PRIORITIES

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
