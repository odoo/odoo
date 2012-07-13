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
import re

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

    def name_create(self, cr, uid, name, context=None):
        """ Overrider of orm's name_create method for partners. The purpose is
            to handle some basic syntaxic tricks to create partners using the
            name_create.
            Supported syntax:
            - 'info@mail.com': create a partner with name info@mail.com, and
              sets its email to info@mail.com
            - 'Raoul Grosbedon <raoul@grosbedon.fr>': create a partner with name
              Raoul Grosbedon, and set its email to raoul@grosbedon.fr
            - anything else: fall back on the default name_create
            Regex :
            - (^|\s)([\w|\.]+)@([\w|\.]*): (void), info, openerp.com
            - (^|\s)([\w|\.|\s]+)[\<]([\w|\.]+)@([\w|\.]*)[\>]: (void), Raoul
              Grosbedon, raoul, grosbedon.fr
        """
        contact_regex = re.compile('(^|\s)([\w|\.|\s]+)[\<]([\w|\.]+)@([\w|\.]*)[\>]')
        email_regex = re.compile('(^|\s)([\w|\.]+)@([\w|\.]*)')
        contact_regex_res = contact_regex.findall(name)
        email_regex_res = email_regex.findall(name)
        if contact_regex_res:
            name = contact_regex_res[0][1]
            name = name.rstrip(' ') # remove extra spaces on the right
            email = '%s@%s' % (contact_regex_res[0][2], contact_regex_res[0][3])
            rec_id = self.create(cr, uid, {self._rec_name: name, 'email': email}, context);
            return self.name_get(cr, uid, [rec_id], context)[0]
        elif email_regex:
            email = '%s@%s' % (email_regex_res[0][1], email_regex_res[0][2])
            rec_id = self.create(cr, uid, {self._rec_name: email, 'email': email}, context);
            return self.name_get(cr, uid, [rec_id], context)[0]
        else:
            return super(res_partner, self).create(cr, uid, name, context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
