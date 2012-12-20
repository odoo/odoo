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
from openerp import tools

from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.osv import fields
from openerp.osv import osv

import crm

class base_action_rule(osv.osv):
    """ Base Action Rule """
    _inherit = 'base.action.rule'
    _description = 'Action Rules'

    _columns = {
        'act_section_id': fields.many2one('crm.case.section', 'Set Team to'),
        'act_categ_id': fields.many2one('crm.case.categ', 'Set Category to'),
    }

    def _process(self, cr, uid, action, record_ids, context=None):
        """ process the given action on the records """
        res = super(base_action_rule, self)._process(cr, uid, action, record_ids, context=context)

        # add record modifications
        context = dict(context or {}, action=True)
        model = self.pool.get(action.model_id.model)
        values = {}
        if action.act_section_id and 'section_id' in model._all_columns:
            values['section_id'] = action.act_section_id.id
        if action.act_categ_id and 'categ_ids' in model._all_columns:
            values['categ_ids'] = [(4, action.act_categ_id.id)]
        model.write(cr, uid, record_ids, values, context=context)

        return res

    def state_get(self, cr, uid, context=None):
        """Gets available states for crm"""
        res = super(base_action_rule, self).state_get(cr, uid, context=context)
        return res + crm.AVAILABLE_STATES

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
