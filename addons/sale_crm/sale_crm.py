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

from openerp.osv import osv, fields

class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = ['sale.order', 'crm.tracking.mixin']
    _columns = {
        'tag_ids': fields.many2many('crm.lead.tag', 'sale_order_tag_rel', 'order_id', 'tag_id', 'Tags'),
        'opportunity_id': fields.many2one('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]")
    }
