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

from osv import osv
from osv import fields

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = ['res.partner', 'mail.thread']
    _columns = {
        'emails': fields.one2many('mail.message', 'partner_id', 'Emails', readonly=True, domain=[('email_from','!=',False)]),
    }

    def message_load_ids(self, cr, uid, ids, limit=100, offset=0, domain=[], ascent=False, root_ids=[False], context=None):
        """ Override of message_load_ids
            User discussion page :
            - messages posted on res.partner, partner_id = user.id
            - messages directly sent to partner
        """
        if context is None:
            context = {}
        msg_obj = self.pool.get('mail.message')
        msg_ids = []
        for user in self.browse(cr, uid, ids, context=context):
            msg_ids += msg_obj.search(cr, uid, [('partner_id', '=', user.id)] + domain,
            limit=limit, offset=offset, context=context)
        if (ascent): msg_ids = self._message_add_ancestor_ids(cr, uid, ids, msg_ids, root_ids, context=context)
        return msg_ids
res_partner()

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
