# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2014 Marcos Organizador de Negocios- Eneldo Serrata - http://marcos.do
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company like Marcos Organizador de Negocios.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
##############################################################################

from openerp.osv.orm import browse_null
from ..tools import is_identification
from openerp.osv import osv, fields
import redis
from redis.exceptions import RedisError
import json
from openerp.osv.expression import get_unaccent_wrapper


class res_partner(osv.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    def _check_unique_ref(self, cr, uid, ids, context=None):
        partner = self.browse(cr, uid, ids, context=context)[0]
        if partner.customer or partner.supplier:
            if partner.is_company and not partner.ref:
                return False
            elif partner.is_company and isinstance(partner.property_account_position, browse_null):
                return False
            elif partner.is_company and is_identification(partner.ref):
                return True
            elif partner.is_company is False:
                return True
        else:
            return True

    _columns = {
        'invoice_method': fields.selection([('manual', 'Se digitaran las facturas manualmente'),
                                            ('order', 'El proveedor envia factura definitiva'),
                                            ('picking', 'El proveedor envia orden de entrega y luego envia la factura')],
                                            'Invoicing Control',
                                           help="Based on Purchase Order lines: place individual lines in 'Invoice Control > Based on P.O. lines' from where you can selectively create an invoice.\n" \
                                            "Based on generated invoice: create a draft invoice you can validate later.\n" \
                                            "Bases on incoming shipments: let you create an invoice when receptions are validated."
        ),
        'multiple_company_rnc': fields.boolean(u"RNC para varias compañias", help=u"Esto permite poder utilizar el RNC en varios registros de compañias")
    }

    _constraints = [
        (osv.osv._check_recursion, 'You cannot create recursive Partner hierarchies.', ['parent_id']),
        # (_check_unique_ref, u"Los datos fiscales no son valido revise RNC/Cédula y la posición fiscal", [u"Rnc/Cédula"]),
    ]

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):

            self.check_access_rights(cr, uid, 'read')
            where_query = self._where_calc(cr, uid, args, context=context)
            self._apply_ir_rules(cr, uid, where_query, 'read', context=context)
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(cr)

            query = """SELECT id
                         FROM res_partner
                      {where} ({email} {operator} {percent}
                           OR {display_name} {operator} {percent})
                     ORDER BY {display_name}
                    """.format(where=where_str, operator=operator,
                               email=unaccent('email'),
                               display_name=unaccent('display_name'),
                               percent=unaccent('%s'))

            where_clause_params += [search_name, search_name]
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            cr.execute(query, where_clause_params)
            ids = map(lambda x: x[0], cr.fetchall())

            if ids:
                return self.name_get(cr, uid, ids, context)
            else:
                return []
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    def create(self, cr, uid, vals, context=None):
        try:
            supplier = context.get('search_default_supplier', False)
            customer = context.get('search_default_customer', False)
            r = redis.StrictRedis(host='localhost', port=6379, db=0)

            if vals.get('ref', False) and not len(vals['ref']) in [9, 11]:
                raise osv.except_osv(u"Debe colocar un numero de RNC/Cedula valido!", u"001")

            elif vals['name'].isdigit() and not len(vals['name']) in [9, 11]:
                raise osv.except_osv(u"Debe colocar un numero de RNC/Cedula valido!", u"002")

            elif (vals.get('ref', False) and self.search(cr, uid, [('ref', '=', vals['ref']), ('multiple_company_rnc', '=', False)])) or \
                    (vals['name'] and self.search(cr, uid, [('ref', '=', vals['name']), ('multiple_company_rnc', '=', False)])):
                raise osv.except_osv(u"Es relacionado ya ha sido registrado! Si quiere utilizar varios relacionados con mismo RNC/Cedula debe indicarlo en el campo --RNC para varias compañias--", u"003")
            elif vals['name'].isdigit() and len(vals['name']) in [9, 11]:
                data = json.loads(r.get(vals['name']))
                if data:
                    vals['ref'] = vals['name']
                    vals['name'] = data['name']
                    vals['street'] = u"%s %s" % (data['street'], data['number'])
                    vals['street1'] = data['sector']
                    vals["comment"] = u"Creada el %s, actividad %s" % (data['establishment'], data['description'])
                    if len(vals['ref']) == 9:
                        vals['is_company'] = True

                    if customer:
                        vals['property_account_position'] = 1
                    elif supplier:
                        vals["property_account_position"] = 13
                else:
                    raise osv.except_osv(u"El numero de RNC/Cedula no es valido", u"")
            elif vals.get('ref', False) and r.get(vals['ref']):
                data = json.loads(r.get(vals['ref']))
                if data:
                    vals['name'] = data['name']
                    vals['street'] = u"%s %s" % (data['street'], data['number'])
                    vals['street1'] = data['sector']
                    vals["comment"] = u"Creada el %s, actividad %s" % (data['establishment'], data['description'])
                    if len(vals['ref']) == 9:
                        vals['is_company'] = True
                        if customer:
                            vals['property_account_position'] = 1
                        elif supplier:
                            vals["property_account_position"] = 13
        except osv.except_osv as e:
            if vals["is_company"] == False:
                pass
            else:
                raise e
        except RedisError:
            pass

        new_id = super(res_partner, self).create(cr, uid, vals, context=context)
        partner = self.browse(cr, uid, new_id, context=context)

        self._fields_sync(cr, uid, partner, vals, context)
        self._handle_first_contact_creation(cr, uid, partner, context)
        return new_id
