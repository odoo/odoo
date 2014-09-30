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

from openerp.osv import orm, fields
from openerp.tools.translate import _


class phone_common(orm.AbstractModel):
    _inherit = 'phone.common'

    def click2dial(self, cr, uid, erp_number, context=None):
        '''
        Inherit the native click2dial function to trigger
        a wizard "Create Call in CRM" via the Javascript code
        of base_phone
        '''
        if context is None:
            context = {}
        res = super(phone_common, self).click2dial(
            cr, uid, erp_number, context=context)
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        if (
                context.get('click2dial_model') == 'res.partner'
                and user.context_propose_creation_crm_call):
            res.update({
                'action_name': _('Create Call in CRM'),
                'action_model': 'wizard.create.crm.phonecall',
                })
        return res


class res_users(orm.Model):
    _inherit = "res.users"

    _columns = {
        # Field name starts with 'context_' to allow modification by the user
        # in his preferences, cf server/openerp/addons/base/res/res_users.py
        # in "def write()" of "class res_users(osv.osv)"
        'context_propose_creation_crm_call': fields.boolean(
            'Propose to create a call in CRM after a click2dial'),
        }

    _defaults = {
        'context_propose_creation_crm_call': True,
        }
