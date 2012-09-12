# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv
from osv import fields


class invite_wizard(osv.osv_memory):
    """ Wizard to invite partners and make them followers. """
    _name = 'mail.wizard.invite'
    _description = 'Invite wizard'

    _columns = {
        'res_model': fields.char('Related Document Model', size=128,
                        required=True, select=1,
                        help='Model of the followed resource'),
        'res_id': fields.integer('Related Document ID', select=1,
                        help='Id of the followed resource'),
        'partner_ids': fields.many2many('res.partner', string='Partners'),
        'message': fields.text('Message'),
    }

    def onchange_partner_ids(self, cr, uid, ids, value, context=None):
        """ onchange_partner_ids (value format: [[6, 0, [3, 4]]]). The
            basic purpose of this method is to check that destination partners
            effectively have email addresses. Otherwise a warning is thrown.
        """
        res = {'value': {}}
        if not value or not value[0] or not value[0][0] == 6:
            return
        res.update(self.pool.get('mail.message').verify_partner_email(cr, uid, value[0][2], context=context))
        return res

    def add_followers(self, cr, uid, ids, context=None):
        for wizard in self.browse(cr, uid, ids, context=context):
            model_obj = self.pool.get(wizard.res_model)
            model_obj.message_subscribe(cr, uid, [wizard.res_id], [p.id for p in wizard.partner_ids], context=context)
        return {'type': 'ir.actions.act_window_close'}
