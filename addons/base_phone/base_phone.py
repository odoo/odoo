# -*- encoding: utf-8 -*-
##############################################################################
#
#    Base Phone module for Odoo/OpenERP
#    Copyright (C) 2010-2014 Alexis de Lattre <alexis@via.ecp.fr>
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

from openerp.osv import orm, fields
from openerp.tools.translate import _
import logging
# Lib for phone number reformating -> pip install phonenumbers
import phonenumbers

_logger = logging.getLogger(__name__)


class phone_common(orm.AbstractModel):
    _name = 'phone.common'

    def generic_phonenumber_to_e164(
            self, cr, uid, ids, field_from_to_seq, context=None):
        result = {}
        from_field_seq = [item[0] for item in field_from_to_seq]
        for record in self.read(cr, uid, ids, from_field_seq, context=context):
            result[record['id']] = {}
            for fromfield, tofield in field_from_to_seq:
                if not record.get(fromfield):
                    res = False
                else:
                    try:
                        res = phonenumbers.format_number(
                            phonenumbers.parse(record.get(fromfield), None),
                            phonenumbers.PhoneNumberFormat.E164)
                    except Exception, e:
                        _logger.error(
                            "Cannot reformat the phone number '%s' to E.164 "
                            "format. Error message: %s"
                            % (record.get(fromfield), e))
                        _logger.error(
                            "You should fix this number and run the wizard "
                            "'Reformat all phone numbers' from the menu "
                            "Settings > Configuration > Phones")
                    # If I raise an exception here, it won't be possible to
                    # install the module on a DB with bad phone numbers
                        res = False
                result[record['id']][tofield] = res
        return result

    def _generic_reformat_phonenumbers(
            self, cr, uid, vals,
            phonefields=[
                'phone', 'partner_phone', 'work_phone', 'fax',
                'mobile', 'partner_mobile', 'mobile_phone',
                ],
            context=None):
        """Reformat phone numbers in E.164 format i.e. +33141981242"""
        if any([vals.get(field) for field in phonefields]):
            user = self.pool['res.users'].browse(cr, uid, uid, context=context)
            # country_id on res.company is a fields.function that looks at
            # company_id.partner_id.addres(default).country_id
            if user.company_id.country_id:
                user_countrycode = user.company_id.country_id.code
            else:
                # We need to raise an exception here because, if we pass None
                # as second arg of phonenumbers.parse(), it will raise an
                # exception when you try to enter a phone number in
                # national format... so it's better to raise the exception here
                raise orm.except_orm(
                    _('Error:'),
                    _("You should set a country on the company '%s'")
                    % user.company_id.name)
            for field in phonefields:
                if vals.get(field):
                    init_value = vals.get(field)
                    try:
                        res_parse = phonenumbers.parse(
                            vals.get(field), user_countrycode)
                    except Exception, e:
                        raise orm.except_orm(
                            _('Error:'),
                            _("Cannot reformat the phone number '%s' to "
                                "international format. Error message: %s")
                            % (vals.get(field), e))
                    vals[field] = phonenumbers.format_number(
                        res_parse, phonenumbers.PhoneNumberFormat.E164)
                    if init_value != vals[field]:
                        _logger.info(
                            "%s initial value: '%s' updated value: '%s'"
                            % (field, init_value, vals[field]))
        return vals

    def get_name_from_phone_number(
            self, cr, uid, presented_number, context=None):
        '''Function to get name from phone number. Usefull for use from IPBX
        to add CallerID name to incoming calls.'''
        res = self.get_record_from_phone_number(
            cr, uid, presented_number, context=context)
        if res:
            return res[2]
        else:
            return False

    def get_record_from_phone_number(
            self, cr, uid, presented_number, context=None):
        '''If it finds something, it returns (object name, ID, record name)
        For example : ('res.partner', 42, u'Alexis de Lattre (Akretion)')
        '''
        if context is None:
            context = {}
        ctx_phone = context.copy()
        ctx_phone['callerid'] = True
        _logger.debug(
            u"Call get_name_from_phone_number with number = %s"
            % presented_number)
        if not isinstance(presented_number, (str, unicode)):
            _logger.warning(
                u"Number '%s' should be a 'str' or 'unicode' but it is a '%s'"
                % (presented_number, type(presented_number)))
            return False
        if not presented_number.isdigit():
            _logger.warning(
                u"Number '%s' should only contain digits." % presented_number)

        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        nr_digits_to_match_from_end = \
            user.company_id.number_of_digits_to_match_from_end
        if len(presented_number) >= nr_digits_to_match_from_end:
            end_number_to_match = presented_number[
                -nr_digits_to_match_from_end:len(presented_number)]
        else:
            end_number_to_match = presented_number

        phonefieldsdict = self._get_phone_fields(cr, uid, context=context)
        phonefieldslist = []
        for objname, prop in phonefieldsdict.iteritems():
            if prop.get('get_name_sequence'):
                phonefieldslist.append({objname: prop})
        phonefieldslist_sorted = sorted(
            phonefieldslist,
            key=lambda element: element.values()[0]['get_name_sequence'])

        for phonedict in phonefieldslist_sorted:
            objname = phonedict.keys()[0]
            prop = phonedict.values()[0]
            phonefields = prop['phonefields']
            obj = self.pool[objname]
            pg_search_number = str('%' + end_number_to_match)
            _logger.debug(
                "Will search phone and mobile numbers in %s ending with '%s'"
                % (objname, end_number_to_match))
            domain = []
            for phonefield in phonefields:
                domain.append((phonefield, 'like', pg_search_number))
            if len(phonefields) > 1:
                domain = ['|'] * (len(phonefields) - 1) + domain
            res_ids = obj.search(cr, uid, domain, context=context)
            if len(res_ids) > 1:
                _logger.warning(
                    u"There are several %s (IDS = %s) with a phone number "
                    "ending with '%s'. Taking the first one."
                    % (objname, res_ids, end_number_to_match))
            if res_ids:
                name = obj.name_get(
                    cr, uid, res_ids[0], context=ctx_phone)[0][1]
                res = (objname, res_ids[0], name)
                _logger.debug(
                    u"Answer get_record_from_phone_number: (%s, %d, %s)"
                    % (res[0], res[1], res[2]))
                return res
            else:
                _logger.debug(
                    u"No match on %s for end of phone number '%s'"
                    % (objname, end_number_to_match))
        return False

    def _get_phone_fields(self, cr, uid, context=None):
        '''Returns a dict with key = object name
        and value = list of phone fields'''
        res = {
            'res.partner': {
                'phonefields': ['phone', 'mobile'],
                'faxfields': ['fax'],
                'get_name_sequence': 10,
                },
            }
        return res

    def click2dial(self, cr, uid, erp_number, context=None):
        '''This function is designed to be overridden in IPBX-specific
        modules, such as asterisk_click2dial'''
        return {'dialed_number': erp_number}


class res_partner(orm.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'phone.common']

    def create(self, cr, uid, vals, context=None):
        vals_reformated = self._generic_reformat_phonenumbers(
            cr, uid, vals, context=context)
        return super(res_partner, self).create(
            cr, uid, vals_reformated, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals_reformated = self._generic_reformat_phonenumbers(
            cr, uid, vals, context=context)
        return super(res_partner, self).write(
            cr, uid, ids, vals_reformated, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('callerid'):
            res = []
            if isinstance(ids, (int, long)):
                ids = [ids]
            for partner in self.browse(cr, uid, ids, context=context):
                if partner.parent_id and partner.parent_id.is_company:
                    name = u'%s (%s)' % (partner.name, partner.parent_id.name)
                else:
                    name = partner.name
                res.append((partner.id, name))
            return res
        else:
            return super(res_partner, self).name_get(
                cr, uid, ids, context=context)


class res_company(orm.Model):
    _inherit = 'res.company'

    _columns = {
        'number_of_digits_to_match_from_end': fields.integer(
            'Number of Digits To Match From End',
            help="In several situations, OpenERP will have to find a "
            "Partner/Lead/Employee/... from a phone number presented by the "
            "calling party. As the phone numbers presented by your phone "
            "operator may not always be displayed in a standard format, "
            "the best method to find the related Partner/Lead/Employee/... "
            "in OpenERP is to try to match the end of the phone number in "
            "OpenERP with the N last digits of the phone number presented "
            "by the calling party. N is the value you should enter in this "
            "field."),
        }

    _defaults = {
        'number_of_digits_to_match_from_end': 8,
        }

    _sql_constraints = [(
        'number_of_digits_to_match_from_end_positive',
        'CHECK (number_of_digits_to_match_from_end > 0)',
        "The value of the field 'Number of Digits To Match From End' must "
        "be positive."),
        ]
