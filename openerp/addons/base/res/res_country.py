# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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


class Country(osv.osv):
    _name = 'res.country'
    _description = 'Country'
    _columns = {
        'name': fields.char('Country Name', size=64,
            help='The full name of the country.', required=True, translate=True),
        'code': fields.char('Country Code', size=2,
            help='The ISO country code in two chars.\n'
            'You can use this field for quick search.', required=True),
        'address_format': fields.text('Address Format')            
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]
    _defaults = {
        'address_format': "%(street)s\n%(street2)s\n%(city)s,%(state_code)s %(zip)s",
    }    

    def name_search(self, cr, user, name='', args=None, operator='ilike',
            context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        ids = False
        if len(name) == 2:
            ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                    limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)] + args,
                    limit=limit, context=context)
        return self.name_get(cr, user, ids, context)
    _order='name'

    def create(self, cursor, user, vals, context=None):
        if 'code' in vals:
            vals['code'] = vals['code'].upper()
        return super(Country, self).create(cursor, user, vals,
                context=context)

    def write(self, cursor, user, ids, vals, context=None):
        if 'code' in vals:
            vals['code'] = vals['code'].upper()
        return super(Country, self).write(cursor, user, ids, vals,
                context=context)

Country()


class CountryState(osv.osv):
    _description="Country state"
    _name = 'res.country.state'
    _columns = {
        'country_id': fields.many2one('res.country', 'Country',
            required=True),
        'name': fields.char('State Name', size=64, required=True),
        'code': fields.char('State Code', size=3,
            help='The state code in three chars.\n', required=True),
    }
    def name_search(self, cr, user, name='', args=None, operator='ilike',
            context=None, limit=100):
        if not args:
            args = []
        if not context:
            context = {}
        ids = self.search(cr, user, [('code', 'ilike', name)] + args, limit=limit,
                context=context)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)] + args,
                    limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

    _order = 'code'
CountryState()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

