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

class general_configuration(osv.osv_memory):
    _name = 'general.configuration'
    _inherit = 'res.config.settings'
    
    _columns = {
        'module_multi_company': fields.boolean('Active Multi company',
                           help ="""It allow to installs the multi_company module."""),
        'module_portal': fields.boolean('Customer Portal',
                           help ="""It installs the portal module."""),
        'module_share': fields.boolean('Share',
                           help ="""It installs the share module."""),
    }

    def base_setup_company(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data_obj = self.pool.get('ir.model.data')
        user = self.pool.get('res.users').browse(cr, uid, uid)
        context.update({'res_id': user.company_id.id})
        company_view_id = data_obj.get_object_reference(cr, uid, 'base', 'view_company_form')
        if company_view_id:
            company_view_id = company_view_id and company_view_id[1] or False
        return {
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'res.company',
            'res_id': int(context.get('res_id')),
            'views': [(company_view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy':True,
            'context': context,
        }

general_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
