# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import osv
from openerp.osv import fields


class ir_ui_menu(osv.osv):
    """ Override of ir.ui.menu class. When adding mail_thread module, each
        new mail.group will create a menu entry. This overrides checks that
        the current user is in the mail.group followers. If not, the menu
        entry is taken off the list of menu ids. This way the user will see
        menu entries for the mail.group he is following.
    """
    _inherit = 'ir.ui.menu'

    _columns = {
        'mail_group_id': fields.many2one('mail.group', 'Mail Group')
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """ Override to take off menu entries (mail.group) the user is not
            following. Access are done using SUPERUSER_ID to avoid access
            rights issues for an internal back-end algorithm. """
        ids = super(ir_ui_menu, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=False)
        partner_id = self.pool.get('res.users').read(cr, uid, [uid], ['partner_id'], context=context)[0]['partner_id'][0]
        follower_obj = self.pool.get('mail.followers')
        for menu in self.browse(cr, uid, ids, context=context):
            if menu.mail_group_id:
                sub_ids = follower_obj.search(cr, SUPERUSER_ID, [
                    ('partner_id', '=', partner_id),
                    ('res_model', '=', 'mail.group'),
                    ('res_id', '=', menu.mail_group_id.id)
                    ], context=context)
                if not sub_ids:
                    ids.remove(menu.id)
        if count:
            return len(ids)
        return ids
