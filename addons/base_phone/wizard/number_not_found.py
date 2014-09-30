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
import logging
import phonenumbers

_logger = logging.getLogger(__name__)


class number_not_found(orm.TransientModel):
    _name = "number.not.found"
    _description = "Number not found"

    _columns = {
        'calling_number': fields.char(
            'Calling Number', size=64, readonly=True,
            help="Phone number of calling party that has been obtained "
            "from Asterisk, in the format used by Asterisk (not E.164)."),
        'e164_number': fields.char(
            'E.164 Number', size=64,
            help="E.164 equivalent of the calling number."),
        'number_type': fields.selection(
            [('phone', 'Fixed'), ('mobile', 'Mobile')],
            'Fixed/Mobile', required=True),
        'to_update_partner_id': fields.many2one(
            'res.partner', 'Partner to Update',
            help="Partner on which the phone number will be written"),
        'current_partner_phone': fields.related(
            'to_update_partner_id', 'phone', type='char',
            relation='res.partner', string='Current Phone', readonly=True),
        'current_partner_mobile': fields.related(
            'to_update_partner_id', 'mobile', type='char',
            relation='res.partner', string='Current Mobile', readonly=True),
        }

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(number_not_found, self).default_get(
                    cr, uid, fields_list, context=context)
        if not res:
            res = {}
        if res.get('calling_number'):
            convert = self.pool['phone.common']._generic_reformat_phonenumbers(
                cr, uid, {'phone': res.get('calling_number')}, context=context)
            parsed_num = phonenumbers.parse(convert.get('phone'))
            res['e164_number'] = phonenumbers.format_number(
                parsed_num, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            number_type = phonenumbers.number_type(parsed_num)
            if number_type == 1:
                res['number_type'] = 'mobile'
            else:
                res['number_type'] = 'phone'
        return res

    def create_partner(self, cr, uid, ids, context=None):
        '''Function called by the related button of the wizard'''
        if context is None:
            context = {}
        wiz = self.browse(cr, uid, ids[0], context=context)
        parsed_num = phonenumbers.parse(wiz.e164_number, None)
        number_type = phonenumbers.number_type(parsed_num)

        context['default_%s' % wiz.number_type] = wiz.e164_number
        action = {
            'name': _('Create New Partner'),
            'view_mode': 'form,tree,kanban',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'nodestroy': False,
            'target': 'current',
            'context': context,
            }
        return action

    def update_partner(self, cr, uid, ids, context=None):
        wiz = self.browse(cr, uid, ids[0], context=context)
        if not wiz.to_update_partner_id:
            raise orm.except_orm(
                _('Error:'),
                _("Select the Partner to Update."))
        self.pool['res.partner'].write(
            cr, uid, wiz.to_update_partner_id.id,
            {wiz.number_type: wiz.e164_number}, context=context)
        action = {
            'name': _('Partner: %s' % wiz.to_update_partner_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form,tree,kanban',
            'nodestroy': False,
            'target': 'current',
            'res_id': wiz.to_update_partner_id.id,
            'context': context,
            }
        return action

    def onchange_to_update_partner(
            self, cr, uid, ids, to_update_partner_id, context=None):
        res = {'value': {}}
        if to_update_partner_id:
            to_update_partner = self.pool['res.partner'].browse(
                cr, uid, to_update_partner_id, context=context)
            res['value'].update({
                'current_partner_phone': to_update_partner.phone,
                'current_partner_mobile': to_update_partner.mobile,
                })
        else:
            res['value'].update({
                'current_partner_phone': False,
                'current_partner_mobile': False,
                })
        return res
