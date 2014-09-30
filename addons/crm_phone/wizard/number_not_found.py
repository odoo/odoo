# -*- encoding: utf-8 -*-
##############################################################################
#
#    Asterisk Click2dial module for OpenERP
#    Copyright (C) 2010-2013 Alexis de Lattre <alexis@via.ecp.fr>
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

from openerp.osv import orm, fields
from openerp.tools.translate import _
import phonenumbers


class number_not_found(orm.TransientModel):
    _inherit = "number.not.found"

    _columns = {
        'to_update_lead_id': fields.many2one(
            'crm.lead', 'Lead to Update',
            domain=[('type', '=', 'lead')],
            help="Lead on which the phone number will be written"),
        'current_lead_phone': fields.related(
            'to_update_lead_id', 'phone', type='char',
            relation='crm.lead', string='Current Phone', readonly=True),
        'current_lead_mobile': fields.related(
            'to_update_lead_id', 'mobile', type='char',
            relation='crm.lead', string='Current Mobile', readonly=True),
        }

    def create_lead(self, cr, uid, ids, context=None):
        '''Function called by the related button of the wizard'''
        if context is None:
            context = {}
        wiz = self.browse(cr, uid, ids[0], context=context)

        action = {
            'name': _('Create New Lead'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form,tree',
            'domain': ['|', ('type', '=', 'lead'), ('type', '=', False)],
            'nodestroy': False,
            'target': 'current',
            'context': {
                'default_%s' % wiz.number_type: wiz.e164_number,
                'default_type': 'lead',
                'stage_type': 'lead',
                'needaction_menu_ref': 'crm.menu_crm_opportunities',
                },
            }
        return action

    def update_lead(self, cr, uid, ids, context=None):
        wiz = self.browse(cr, uid, ids[0], context=context)
        if not wiz.to_update_lead_id:
            raise orm.except_orm(
                _('Error:'),
                _("Select the Lead to Update."))
        self.pool['crm.lead'].write(
            cr, uid, wiz.to_update_lead_id.id,
            {wiz.number_type: wiz.e164_number}, context=context)
        action = {
            'name': _('Lead: %s' % wiz.to_update_lead_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form,tree',
            'nodestroy': False,
            'target': 'current',
            'res_id': wiz.to_update_lead_id.id,
            'context': {
                'stage_type': 'lead',
                'needaction_menu_ref': 'crm.menu_crm_opportunities',
                },
            }
        return action

    def onchange_to_update_lead(
            self, cr, uid, ids, to_update_lead_id, context=None):
        res = {'value': {}}
        if to_update_lead_id:
            to_update_lead = self.pool['crm.lead'].browse(
                cr, uid, to_update_lead_id, context=context)
            res['value'].update({
                'current_lead_phone': to_update_lead.phone,
                'current_lead_mobile': to_update_lead.mobile,
                })
        else:
            res['value'].update({
                'current_lead_phone': False,
                'current_lead_mobile': False,
                })
        return res
