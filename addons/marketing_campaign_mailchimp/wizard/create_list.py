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
from tools.translate import _
import netsvc

class create_list(osv.osv_memory):
    _name = "create.list"
    _description = "Create List of mailchimp"
# crm.lead remain
    _columns = {
        'mailchimp_account_id': fields.many2one('mailchimp.account',
                                             'Mailchimp Account', required=True),
        'mailchimp_list_id': fields.many2one('mailchimp.list', 'List'),
        'list_name': fields.char('Name',size = 64),
        'partner_ids': fields.many2many('res.partner',
                                        'create_list_partner_rel',
                                        'cust_list_id', 'partner_id',
                                        'Partner'),

        }

    def onchange_mailchimp_account_id(self, cr, uid, ids, mailchimp_account_id,
                                                                action):
        return {'value':{}}

    def create_list(self, cr, uid, ids, context=None):
        create_list_obj = self.browse(cr, uid, ids[0])
        mailchimp_account_obj = self.pool.get('mailchimp.account')
        account_id = create_list_obj.mailchimp_account_id
        lists = mailchimp_account_obj.get_response(cr, uid, account_id.id, 'lists')
        lists = dict([(l['name'],l['id']) for l in lists])
        if create_list_obj.list_name not in lists.keys():
            raise  osv.except_osv(_('UserError'),
                _('There is no list define in account %s') % (account_id.name))
        list_id = lists[create_list_obj.list_name]
        mailchimp_account_obj.add_partner_list(cr, uid, account_id.id, list_id,
                                                    create_list_obj.partner_ids)
        return {}
create_list()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
