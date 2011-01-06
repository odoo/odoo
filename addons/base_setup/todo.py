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
from operator import itemgetter

from osv import osv, fields
import netsvc
import tools

class base_setup_company(osv.osv_memory):
    """
    """
    _name = 'base.setup.company'
    _inherit = 'res.config'
    logger = netsvc.Logger()

    def _get_all(self, cr, uid, model, context=None):
        models = self.pool.get(model)
        all_model_ids = models.search(cr, uid, [])

        output = [(False, '')]
        output.extend(
            sorted([(o.id, o.name)
                    for o in models.browse(cr, uid, all_model_ids,
                                           context=context)],
                   key=itemgetter(1)))
        return output

    def _get_all_states(self, cr, uid, context=None):
        return self._get_all(
            cr, uid, 'res.country.state', context=context)
    def _get_all_countries(self, cr, uid, context=None):
        return self._get_all(cr, uid, 'res.country', context=context)

    def _show_company_data(self, cr, uid, context=None):
        # We only want to show the default company data in demo mode, otherwise users tend to forget
        # to fill in the real company data in their production databases
        return self.pool.get('ir.model.data').get_object(cr, uid, 'base', 'module_meta_information').demo


    def default_get(self, cr, uid, fields_list=None, context=None):
        """ get default company if any, and the various other fields
        from the company's fields
        """
        defaults = super(base_setup_company, self)\
              .default_get(cr, uid, fields_list=fields_list, context=context)
        companies = self.pool.get('res.company')
        company_id = companies.search(cr, uid, [], limit=1, order="id")
        if not company_id or 'company_id' not in fields_list:
            return defaults
        company = companies.browse(cr, uid, company_id[0], context=context)
        defaults['company_id'] = company.id

        if not self._show_company_data(cr, uid, context=context):
            return defaults

        defaults['currency'] = company.currency_id.id
        for field in ['name','logo','rml_header1','rml_footer1','rml_footer2']:
            defaults[field] = company[field]

        if company.partner_id.address:
            address = company.partner_id.address[0]
            for field in ['street','street2','zip','city','email','phone']:
                defaults[field] = address[field]
            for field in ['country_id','state_id']:
                if address[field]:
                    defaults[field] = address[field].id

        return defaults

    _columns = {
        'company_id':fields.many2one('res.company', 'Company'),
        'name':fields.char('Company Name', size=64, required=True),
        'street':fields.char('Street', size=128),
        'street2':fields.char('Street 2', size=128),
        'zip':fields.char('Zip Code', size=24),
        'city':fields.char('City', size=128),
        'state_id':fields.selection(_get_all_states, 'Fed. State'),
        'country_id':fields.selection(_get_all_countries, 'Country'),
        'email':fields.char('E-mail', size=64),
        'phone':fields.char('Phone', size=64),
        'currency':fields.many2one('res.currency', 'Currency', required=True),
        'rml_header1':fields.char('Report Header', size=200,
            help='''This sentence will appear at the top right corner of your reports.
We suggest you to put a slogan here:
"Open Source Business Solutions".'''),
        'rml_footer1':fields.char('Report Footer 1', size=200,
            help='''This sentence will appear at the bottom of your reports.
We suggest you to write legal sentences here:
Web: http://openerp.com - Fax: +32.81.73.35.01 - Fortis Bank: 126-2013269-07'''),
        'rml_footer2':fields.char('Report Footer 2', size=200,
            help='''This sentence will appear at the bottom of your reports.
We suggest you to put bank information here:
IBAN: BE74 1262 0121 6907 - SWIFT: CPDF BE71 - VAT: BE0477.472.701'''),
        'logo':fields.binary('Logo'),
        'account_no':fields.char('Bank Account No', size=64),
        'website': fields.char('Company Website', size=64, help="Example: http://openerp.com"),
    }

    def execute(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "We should only get one object from the form"
        payload = self.browse(cr, uid, ids[0], context=context)
        if not getattr(payload, 'company_id', None):
            raise ValueError('Case where no default main company is setup '
                             'not handled yet')
        company = payload.company_id
        company.write({
            'name':payload.name,
            'rml_header1':payload.rml_header1,
            'rml_footer1':payload.rml_footer1,
            'rml_footer2':payload.rml_footer2,
            'logo':payload.logo,
            'currency_id':payload.currency.id,
            'account_no':payload.account_no,
        })

        company.partner_id.write({
            'name':payload.name,
            'website':payload.website,
        })

        address_data = {
            'name':payload.name,
            'street':payload.street,
            'street2':payload.street2,
            'zip':payload.zip,
            'city':payload.city,
            'email':payload.email,
            'phone':payload.phone,
            'country_id':int(payload.country_id),
            'state_id':int(payload.state_id),
        }

        if company.partner_id.address:
            company.partner_id.address[0].write(
                address_data)
        else:
            self.pool.get('res.partner.address').create(cr, uid,
                    dict(address_data,
                         partner_id=int(company.partner_id)),
                    context=context)
base_setup_company()

class res_currency(osv.osv):
    _inherit = 'res.currency'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
#        We can use the following line,if we want to restrict this name_get for company setup only
#        But, its better to show currencies as name(Code).
        if not len(ids):
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','symbol'], context, load='_classic_write')
        return [(x['id'], tools.ustr(x['name']) + (x['symbol'] and (' (' + tools.ustr(x['symbol']) + ')') or '')) for x in reads]

res_currency()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
