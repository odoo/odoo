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
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.thread']
    _columns = {
        'emails': fields.one2many('mail.message', 'partner_id', 'Emails', readonly=True, domain=[('email_from','!=',False)]),
    }

    def message_search_get_domain(self, cr, uid, ids, context=None):
        """ Override of message_search_get_domain for partner discussion page.
            The purpose is to add messages directly sent to the partner.
        """
        initial_domain = super(res_partner, self).message_search_get_domain(cr, uid, ids, context=context)
        if self._name == 'res.partner': # to avoid models inheriting from res.partner
            search_domain = ['|'] + initial_domain + [('partner_id', 'in', ids)]
        return search_domain

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
