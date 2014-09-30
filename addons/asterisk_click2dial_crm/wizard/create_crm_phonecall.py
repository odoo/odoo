# -*- encoding: utf-8 -*-
##############################################################################
#
#    Asterisk click2dial CRM module for OpenERP
#    Copyright (c) 2012-2014 Akretion (http://www.akretion.com)
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp.osv import orm


class wizard_create_crm_phonecall(orm.TransientModel):
    _name = "wizard.create.crm.phonecall"

    def button_create_outgoing_phonecall(self, cr, uid, ids, context=None):
        partner = self.pool['res.partner'].browse(
            cr, uid, context.get('partner_id'), context=context)
        return self._create_open_crm_phonecall(
            cr, uid, partner, crm_categ='Outbound', context=context)

    def _create_open_crm_phonecall(
            self, cr, uid, partner, crm_categ, context=None):
        if context is None:
            context = {}
        categ_ids = self.pool['crm.case.categ'].search(
            cr, uid, [('name', '=', crm_categ)], context={'lang': 'en_US'})
        case_section_ids = self.pool['crm.case.section'].search(
            cr, uid, [('member_ids', 'in', uid)], context=context)
        context.update({
            'default_partner_id': partner.id or False,
            'default_partner_phone': partner.phone,
            'default_partner_mobile': partner.mobile,
            'default_categ_id': categ_ids and categ_ids[0] or False,
            'default_section_id':
            case_section_ids and case_section_ids[0] or False,
        })

        return {
            'name': partner.name,
            'domain': [('partner_id', '=', partner.id)],
            'res_model': 'crm.phonecall',
            'view_mode': 'form,tree',
            'type': 'ir.actions.act_window',
            'nodestroy': False,  # close the pop-up wizard after action
            'target': 'current',
            'context': context,
        }
