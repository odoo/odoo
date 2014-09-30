# -*- coding: utf-8 -*-
##############################################################################
#
#    Base Phone Pop-up module for Odoo/OpenERP
#    Copyright (C) 2014 Alexis de Lattre <alexis@via.ecp.fr>
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


logger = logging.getLogger(__name__)


class phone_common(orm.AbstractModel):
    _inherit = 'phone.common'

    def _prepare_incall_pop_action(
            self, cr, uid, record_res, number, context=None):
        action = False
        if record_res:
            obj = self.pool[record_res[0]]
            action = {
                'name': obj._description,
                'type': 'ir.actions.act_window',
                'res_model': record_res[0],
                'view_mode': 'form,tree',
                'views': [[False, 'form']],  # Beurk, but needed
                'target': 'new',
                'res_id': record_res[1],
                }
        else:
            action = {
                'name': _('Number Not Found'),
                'type': 'ir.actions.act_window',
                'res_model': 'number.not.found',
                'view_mode': 'form',
                'views': [[False, 'form']],  # Beurk, but needed
                'target': 'new',
                'context': {'default_calling_number': number}
            }
        return action

    def incall_notify_by_login(
            self, cr, uid, number, login_list, context=None):
        assert isinstance(login_list, list), 'login_list must be a list'
        res = self.get_record_from_phone_number(
            cr, uid, number, context=context)
        user_ids = self.pool['res.users'].search(
            cr, uid, [('login', 'in', login_list)], context=context)
        logger.debug(
            'Notify incoming call from number %s to users %s'
            % (number, user_ids))
        action = self._prepare_incall_pop_action(
            cr, uid, res, number, context=context)
        if action:
            users = self.pool['res.users'].read(
                cr, uid, user_ids, ['context_incall_popup'], context=context)
            for user in users:
                if user['context_incall_popup']:
                    self.pool['action.request'].notify(
                        cr, uid, to_id=user['id'], **action)
                    logger.debug(
                        'This action has been sent to user ID %d: %s'
                        % (user['id'], action))
        if res:
            callerid = res[2]
        else:
            callerid = False
        return callerid


class res_users(orm.Model):
    _inherit = 'res.users'

    _columns = {
        'context_incall_popup': fields.boolean('Pop-up on Incoming Calls'),
        }

    _defaults = {
        'context_incall_popup': True,
        }
