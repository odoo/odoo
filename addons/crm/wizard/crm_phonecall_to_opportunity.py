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

from osv import osv, fields
from tools.translate import _

class crm_phonecall2opportunity(osv.osv_memory):
    """ Converts Phonecall to Opportunity"""

    _name = 'crm.phonecall2opportunity'
    _inherit = 'crm.partner2opportunity'
    _description = 'Phonecall To Opportunity'

    def make_opportunity(self, cr, uid, ids, context=None):
        """
        This converts Phonecall to Opportunity and opens Phonecall view
        """
        if not len(ids):
            return False
        call_ids = context and context.get('active_ids', False) or False
        this = self.browse(cr, uid, ids[0], context=context)
        if not call_ids:
            return {}
        opportunity = self.pool.get('crm.lead')
        phonecall = self.pool.get('crm.phonecall')
        opportunity_ids = phonecall.convert_opportunity(cr, uid, call_ids, this.name, this.partner_id and this.partner_id.id or False, \
            this.planned_revenue, this.probability, context=context)
        return opportunity.redirect_opportunity_view(cr, uid, opportunity_ids[call_ids[0]], context=context)

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        record_id = context and context.get('active_id', False) or False
        res = super(crm_phonecall2opportunity, self).default_get(cr, uid, fields, context=context)

        if record_id:
            phonecall = self.pool.get('crm.phonecall').browse(cr, uid, record_id, context=context)
            if 'name' in fields:
                res.update({'name': phonecall.name})
            if 'partner_id' in fields:
                res.update({'partner_id': phonecall.partner_id and phonecall.partner_id.id or False})
        return res

crm_phonecall2opportunity()
