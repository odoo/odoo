# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import logging

from openerp.osv import fields, osv
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)


def location_name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
    if not args:
        args = []

    ids = []
    if len(name) == 2:
        ids = self.search(cr, user, [('code', 'ilike', name)] + args,
                          limit=limit, context=context)

    search_domain = [('name', operator, name)]
    if ids:
        search_domain.append(('id', 'not in', ids))
    ids.extend(self.search(cr, user, search_domain + args,
                           limit=limit, context=context))

    locations = self.name_get(cr, user, ids, context)
    return sorted(locations, key=lambda (id, name): ids.index(id))


class Country(osv.osv):
    _name = 'res.country'
    _description = 'Country'
    _columns = {
        'name': fields.char('Country Name',
                            help='The full name of the country.', required=True, translate=True),
        'code': fields.char('Country Code', size=2,
                            help='The ISO country code in two chars.\n'
                            'You can use this field for quick search.'),
        'address_format': fields.text('Address Format', help="""You can state here the usual format to use for the \
addresses belonging to this country.\n\nYou can use the python-style string patern with all the field of the address \
(for example, use '%(street)s' to display the field 'street') plus
            \n%(state_name)s: the name of the state
            \n%(state_code)s: the code of the state
            \n%(country_name)s: the name of the country
            \n%(country_code)s: the code of the country"""),
        'currency_id': fields.many2one('res.currency', 'Currency'),
        'image': fields.binary("Image", attachment=True),
        'phone_code': fields.integer('Country Calling Code'),
        'country_group_ids': fields.many2many('res.country.group', 'res_country_res_country_group_rel', 'res_country_id', 'res_country_group_id', string='Country Groups'),
        'state_ids': fields.one2many('res.country.state', 'country_id', string='States'),
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]
    _defaults = {
        'address_format': "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s",
    }
    _order = 'name'

    name_search = location_name_search

    def create(self, cursor, user, vals, context=None):
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return super(Country, self).create(cursor, user, vals, context=context)

    def write(self, cursor, user, ids, vals, context=None):
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        return super(Country, self).write(cursor, user, ids, vals, context=context)

    def get_address_fields(self, cr, uid, ids, context=None):
        res = {}
        for country in self.browse(cr, uid, ids, context=context):
            res[country.id] = re.findall('\((.+?)\)', country.address_format)
        return res


class CountryGroup(osv.osv):
    _description = "Country Group"
    _name = 'res.country.group'
    _columns = {
        'name': fields.char('Name', required=True),
        'country_ids': fields.many2many('res.country', 'res_country_res_country_group_rel', 'res_country_group_id', 'res_country_id', string='Countries'),
    }


class CountryState(osv.osv):
    _description = "Country state"
    _name = 'res.country.state'
    _columns = {
        'country_id': fields.many2one('res.country', 'Country', required=True),
        'name': fields.char('State Name', required=True,
                            help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton'),
        'code': fields.char('State Code', help='The state code.', required=True),
    }
    _order = 'code'

    name_search = location_name_search

    def merge_states(self, cr, uid, ids=None, context=None):
        Imd = self.pool['ir.model.data']
        State = self.pool['res.country.state']

        query = """
            SELECT st.id, st.oldid, imd.id, imd.name, imd2.id, ids
            FROM (
                SELECT st.country_id, st.code, max(st.id) as id, min(st.id) as oldid, string_agg(cast(id as text), ',') as ids
                FROM res_country_state st
                GROUP BY st.country_id, st.code
                HAVING count(*) > 1
            ) st
                LEFT JOIN ir_model_data imd on (imd.model = 'res.country.state' and imd.res_id = st.id)
                LEFT JOIN ir_model_data imd2 on (imd2.model = 'res.country.state' and imd2.res_id = st.oldid)
            WHERE imd.module = 'base';
        """
        cr.execute(query)
        data = cr.fetchall()

        for st_id, st_oldid, imd_id, imd_name, imd2_id, ids in data:
            values = dict(module=self._module)
            if imd2_id:
                # If duplicated record had already a xml_id we update the old xml_id and
                # force to delete the new xml_id created to avoid constraint error
                keepid = imd2_id
                Imd.unlink(cr, uid, imd_id, context=context)
                values.update(name=imd_name)
            else:
                # Else we point the new xml_id to the oldest duplicated state
                keepid = imd_id
                values.update(res_id=st_oldid)

            Imd.write(cr, uid, keepid, values, context=context)
            State.unlink(cr, uid, st_id, context=context)

            duplicated_ids = set(map(int, ids.split(','))) - set([st_id, st_oldid])
            if duplicated_ids:
                _logger.warning(_('State with id [%s] (%s) seems to have duplicated code: %s' % (st_oldid, imd_name, ','.join(duplicated_ids))))

        if data:
            self._add_sql_constraints(cr)

    _sql_constraints = [
        ('name_code_uniq', 'unique(country_id, code)', 'The code of the state must be unique by country !')
    ]
