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
from tools.translate import _

class Bank(osv.osv):
    _description='Bank'
    _name = 'res.bank'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state': fields.many2one("res.country.state", 'Fed. State',
            domain="[('country_id', '=', country)]"),
        'country': fields.many2one('res.country', 'Country'),
        'email': fields.char('Email', size=64),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'active': fields.boolean('Active'),
        'bic': fields.char('Bank Identifier Code', size=64,
            help="Sometimes called BIC or Swift."),
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


class res_partner_bank_type(osv.osv):
    _description='Bank Account Type'
    _name = 'res.partner.bank.type'
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'code': fields.char('Code', size=64, required=True),
        'field_ids': fields.one2many('res.partner.bank.type.field', 'bank_type_id', 'Type Fields'),
        'format_layout': fields.text('Format Layout', translate=True)
    }
    _defaults = {
        'format_layout': lambda *args: "%(bank_name)s: %(acc_number)s"
    }
res_partner_bank_type()

class res_partner_bank_type_fields(osv.osv):
    _description='Bank type fields'
    _name = 'res.partner.bank.type.field'
    _order = 'name'
    _columns = {
        'name': fields.char('Field Name', size=64, required=True, translate=True),
        'bank_type_id': fields.many2one('res.partner.bank.type', 'Bank Type', required=True, ondelete='cascade'),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
        'size': fields.integer('Max. Size'),
    }
res_partner_bank_type_fields()


class res_partner_bank(osv.osv):
    '''Bank Accounts'''
    _name = "res.partner.bank"
    _rec_name = "acc_number"
    _description = __doc__
    _order = 'sequence'

    def _bank_type_get(self, cr, uid, context=None):
        bank_type_obj = self.pool.get('res.partner.bank.type')

        result = []
        type_ids = bank_type_obj.search(cr, uid, [])
        bank_types = bank_type_obj.browse(cr, uid, type_ids, context=context)
        for bank_type in bank_types:
            result.append((bank_type.code, bank_type.name))
        return result

    def _default_value(self, cursor, user, field, context=None):
        if context is None: context = {}
        if field in ('country_id', 'state_id'):
            value = False
        else:
            value = ''
        if not context.get('address'):
            return value

        for address in self.pool.get('res.partner').resolve_o2m_commands_to_record_dicts(
            cursor, user, 'address', context['address'], ['type', field], context=context):

            if address.get('type') == 'default':
                return address.get(field, value)
            elif not address.get('type'):
                value = address.get(field, value)
        return value

    _columns = {
        'name': fields.char('Bank Account', size=64), # to be removed in v6.2 ?
        'acc_number': fields.char('Account Number', size=64, required=True),
        'bank': fields.many2one('res.bank', 'Bank'),
        'bank_bic': fields.char('Bank Identifier Code', size=16),
        'bank_name': fields.char('Bank Name', size=32),
        'owner_name': fields.char('Account Owner Name', size=128),
        'street': fields.char('Street', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'country_id': fields.many2one('res.country', 'Country',
            change_default=True),
        'state_id': fields.many2one("res.country.state", 'Fed. State',
            change_default=True, domain="[('country_id','=',country_id)]"),
        'company_id': fields.many2one('res.company', 'Company',
            ondelete='cascade', help="Only if this bank account belong to your company"),
        'partner_id': fields.many2one('res.partner', 'Account Owner', required=True,
            ondelete='cascade', select=True),
        'state': fields.selection(_bank_type_get, 'Bank Account Type', required=True,
            change_default=True),
        'sequence': fields.integer('Sequence'),
        'footer': fields.boolean("Display on Reports", help="Display this bank account on the footer of printed documents like invoices and sales orders.")
    }

    _defaults = {
        'owner_name': lambda obj, cursor, user, context: obj._default_value(
            cursor, user, 'name', context=context),
        'street': lambda obj, cursor, user, context: obj._default_value(
            cursor, user, 'street', context=context),
        'city': lambda obj, cursor, user, context: obj._default_value(
            cursor, user, 'city', context=context),
        'zip': lambda obj, cursor, user, context: obj._default_value(
            cursor, user, 'zip', context=context),
        'country_id': lambda obj, cursor, user, context: obj._default_value(
            cursor, user, 'country_id', context=context),
        'state_id': lambda obj, cursor, user, context: obj._default_value(
            cursor, user, 'state_id', context=context),
        'name': lambda *args: '/'
    }

    def fields_get(self, cr, uid, fields=None, context=None):
        res = super(res_partner_bank, self).fields_get(cr, uid, fields, context)
        bank_type_obj = self.pool.get('res.partner.bank.type')
        type_ids = bank_type_obj.search(cr, uid, [])
        types = bank_type_obj.browse(cr, uid, type_ids)
        for type in types:
            for field in type.field_ids:
                if field.name in res:
                    res[field.name].setdefault('states', {})
                    res[field.name]['states'][type.code] = [
                            ('readonly', field.readonly),
                            ('required', field.required)]
        return res

    def _prepare_name_get(self, cr, uid, bank_type_obj, bank_obj, context=None):
        """
        Format the name of a res.partner.bank.
        This function is designed to be inherited to add replacement fields.
        :param browse_record bank_type_obj: res.partner.bank.type object
        :param browse_record bank_obj: res.partner.bank object
        :rtype: str
        :return: formatted name of a res.partner.bank record
        """
        return bank_type_obj.format_layout % bank_obj._data[bank_obj.id]

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        bank_type_obj = self.pool.get('res.partner.bank.type')
        res = []
        for val in self.browse(cr, uid, ids, context=context):
            result = val.acc_number
            if val.state:
                type_ids = bank_type_obj.search(cr, uid, [('code','=',val.state)])
                if type_ids:
                    t = bank_type_obj.browse(cr, uid, type_ids[0], context=context)
                    try:
                        # avoid the default format_layout to result in "False: ..."
                        if not val._data[val.id]['bank_name']:
                            val._data[val.id]['bank_name'] = _('BANK')
                        result = self._prepare_name_get(cr, uid, t, val, context=context)
                    except:
                        result += ' [Formatting Error]'
                        raise osv.except_osv(_("Error"), _("You cannot avoid default format_layout to result in True"))
            res.append((val.id, result))
        return res

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        result = {}
        if company_id:
            c = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            if c.partner_id:
                r = self.onchange_partner_id(cr, uid, ids, c.partner_id.id, context=context)
                r['value']['partner_id'] = c.partner_id.id
                r['value']['footer'] = 1
                result = r
        return result

    def onchange_bank_id(self, cr, uid, ids, bank_id, context=None):
        result = {}
        if bank_id:
            bank = self.pool.get('res.bank').browse(cr, uid, bank_id, context=context)
            result['bank_name'] = bank.name
            result['bank_bic'] = bank.bic
        return {'value': result}


    def onchange_partner_id(self, cr, uid, id, partner_id, context=None):
        result = {}
        if partner_id:
            part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            result['owner_name'] = part.name
            result['street'] = part.street or False
            result['city'] = part.city or False
            result['zip'] =  part.zip or False
            result['country_id'] =  part.country_id.id
            result['state_id'] = part.state_id.id
        return {'value': result}

res_partner_bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
