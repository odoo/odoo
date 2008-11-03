# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv


class Bank(osv.osv):
    _description='Bank'
    _name = 'res.bank'
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'code': fields.char('Code', size=64),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state': fields.many2one("res.country.state", 'State',
            domain="[('country_id', '=', country)]"),
        'country': fields.many2one('res.country', 'Country'),
        'email': fields.char('E-Mail', size=64),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'active': fields.boolean('Active'),
        'bic': fields.char('BIC/Swift code', size=11,
            help="Bank Identifier Code"),
    }
    _defaults = {
        'active': lambda *a: 1,
    }
    def name_get(self, cr, uid, ids, context=None):
        result = []
        for bank in self.browse(cr, uid, ids, context):
            result.append((bank.id, (bank.bic and (bank.bic + ' - ') or '') + bank.name))
        return result

Bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

