# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Adapted by Noviat to 
#     - make the 'mand_id' field optional
#     - support Noviat tax code scheme
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
import time
import base64

from osv import osv, fields
from tools.translate import _
from report import report_sxw

class partner_vat_intra(osv.osv_memory):
    """
    Partner Vat Intra
    """
    _name = "partner.vat.intra"
    _description = 'Partner VAT Intra'

    def _get_xml_data(self, cr, uid, context=None):
        if context.get('file_save', False):
            return base64.encodestring(context['file_save'].encode('utf8'))
        return ''

    def _get_europe_country(self, cursor, user, context=None):
        return self.pool.get('res.country').search(cursor, user, [('code', 'in', ['AT', 'BG', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB'])])

    _columns = {
        'name': fields.char('File Name', size=32),
        'period_code': fields.char('Period Code',size = 6,required = True, help = '''This is where you have to set the period code for the intracom declaration using the format: ppyyyy
      PP can stand for a month: from '01' to '12'.
      PP can stand for a trimester: '31','32','33','34'
          The first figure means that it is a trimester,
          The second figure identify the trimester.
      PP can stand for a complete fiscal year: '00'.
      YYYY stands for the year (4 positions).
    '''
    ),
        'period_ids': fields.many2many('account.period', 'account_period_rel', 'acc_id', 'period_id', 'Period (s)', help = 'Select here the period(s) you want to include in your intracom declaration'),
        'tax_code_id': fields.many2one('account.tax.code', 'Company', domain=[('parent_id', '=', False)], help="Keep empty to use the user's company", required=True),
        'test_xml': fields.boolean('Test XML file', help="Sets the XML output as test file"),
        'mand_id' : fields.char('Reference', size=14, help="Reference given by the Representative of the sending company."),
        'msg': fields.text('File created', size=14, readonly=True),
        'no_vat': fields.text('Partner With No VAT', size=14, readonly=True, help="The Partner whose VAT number is not defined they doesn't include in XML File."),
        'file_save' : fields.binary('Save File', readonly=True),
        'country_ids': fields.many2many('res.country', 'vat_country_rel', 'vat_id', 'country_id', 'European Countries'),
        'comments': fields.text('Comments'),
        }

    def _get_tax_code(self, cr, uid, context=None):
        obj_tax_code = self.pool.get('account.tax.code')
        obj_user = self.pool.get('res.users')
        company_id = obj_user.browse(cr, uid, uid, context=context).company_id.id
        tax_code_ids = obj_tax_code.search(cr, uid, [('company_id', '=', company_id), ('parent_id', '=', False)], context=context)
        return tax_code_ids and tax_code_ids[0] or False

    _defaults = {
        'country_ids': _get_europe_country,
        'file_save': _get_xml_data,
        'name': 'vat_intra.xml',
        'tax_code_id': _get_tax_code,
    }

    def _get_datas(self, cr, uid, ids, context=None):
        """Collects require data for vat intra xml
        :param ids: id of wizard.
        :return: dict of all data to be used to generate xml for Partner VAT Intra.
        :rtype: dict
        """
        if context is None:
            context = {}

        obj_user = self.pool.get('res.users')
        obj_sequence = self.pool.get('ir.sequence')
        obj_partner = self.pool.get('res.partner')
        obj_partner_add = self.pool.get('res.partner.address')

        xmldict = {}
        post_code = street = city = country = data_clientinfo = ''
        seq = amount_sum = 0

        wiz_data = self.browse(cr, uid, ids[0], context=context)
        comments = wiz_data.comments

        if wiz_data.tax_code_id:
            data_company = wiz_data.tax_code_id.company_id
        else:
            data_company = obj_user.browse(cr, uid, uid, context=context).company_id
        
        # Get Company vat
        company_vat = data_company.partner_id.vat
        if not company_vat:
            raise osv.except_osv(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))
        company_vat = company_vat.replace(' ','').upper()
        issued_by = company_vat[:2]

        if len(wiz_data.period_code) != 6:
            raise osv.except_osv(_('Wrong Period Code'), _('The period code you entered is not valid.'))

        if not wiz_data.period_ids:
            raise osv.except_osv(_('Data Insufficient!'),_('Please select at least one Period.'))

        p_id_list = obj_partner.search(cr, uid, [('vat','!=',False)], context=context)
        if not p_id_list:
            raise osv.except_osv(_('Data Insufficient!'),_('No partner has a VAT Number asociated with him.'))

        seq_declarantnum = obj_sequence.get(cr, uid, 'declarantnum')
        dnum = company_vat[2:] + seq_declarantnum[-4:]

        addr = obj_partner.address_get(cr, uid, [data_company.partner_id.id], ['invoice'])
        email = data_company.partner_id.email or ''
        phone = data_company.partner_id.phone or ''

        if addr.get('invoice',False):
            ads = obj_partner_add.browse(cr, uid, [addr['invoice']])[0]
            city = (ads.city or '')
            post_code = (ads.zip or '')
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ' '
                street += ads.street2
            if ads.country_id:
                country = ads.country_id.code

        if not country:
            country = company_vat[:2]
        if not email:
            raise osv.except_osv(_('Data Insufficient!'),_('No email address associated with the company.'))
        if not phone:
            raise osv.except_osv(_('Data Insufficient!'),_('No phone associated with the company.'))
        xmldict.update({
                        'company_name': data_company.name,
                        'company_vat': company_vat, 
                        'vatnum':  company_vat[2:],
                        'mand_id': wiz_data.mand_id, 
                        'sender_date': str(time.strftime('%Y-%m-%d')),
                        'street': street,
                        'city': city,
                        'post_code': post_code,
                        'country': country,
                        'email': email,
                        'phone': phone.replace('/','').replace('.','').replace('(','').replace(')','').replace(' ',''),
                        'period': wiz_data.period_code,
                        'clientlist': [], 
                        'comments': comments,
                        'issued_by': issued_by,
                        })
        #tax code 44: services
        #tax code 46L: normal good deliveries
        #tax code 46T: ABC good deliveries
        #tax code 48xxx: credite note on tax code xxx
        codes = ('44', '46L', '46T', '48s44', '48s46L', '48s46T')
        cr.execute('''SELECT p.name As partner_name, l.partner_id AS partner_id, p.vat AS vat, 
                      (CASE WHEN t.code = '48s44' THEN '44'
                            WHEN t.code = '48s46L' THEN '46L'
                            WHEN t.code = '48s46T' THEN '46T'
                       ELSE t.code END) AS intra_code,
                      SUM(CASE WHEN t.code in ('48s44','48s46L','48s46T') THEN -l.tax_amount ELSE l.tax_amount END) AS amount
                      FROM account_move_line l
                      LEFT JOIN account_tax_code t ON (l.tax_code_id = t.id)
                      LEFT JOIN res_partner p ON (l.partner_id = p.id)
                      WHERE t.code IN %s
                       AND l.period_id IN %s
                       AND t.company_id = %s
                      GROUP BY p.name, l.partner_id, p.vat, intra_code''', (codes, tuple([p.id for p in wiz_data.period_ids]), data_company.id))

        p_count = 0

        for row in cr.dictfetchall():
            if not row['vat']:
                row['vat'] = ''
                p_count += 1

            seq += 1
            amt = row['amount'] or 0.0
            amount_sum += amt

            intra_code = row['intra_code'] == '44' and 'S' or (row['intra_code'] == '46L' and 'L' or (row['intra_code'] == '46T' and 'T' or ''))

            xmldict['clientlist'].append({
                                        'partner_name': row['partner_name'],
                                        'seq': seq, 
                                        'vatnum': row['vat'][2:].replace(' ','').upper(), 
                                        'vat': row['vat'],
                                        'country': row['vat'][:2],
                                        'amount': amt,
                                        'intra_code': row['intra_code'],
                                        'code': intra_code})

        xmldict.update({'dnum': dnum, 'clientnbr': str(seq), 'amountsum': amount_sum, 'partner_wo_vat': p_count})
        return xmldict

    def create_xml(self, cursor, user, ids, context=None):
        """Creates xml that is to be exported and sent to estate for partner vat intra.
        :return: Value for next action.
        :rtype: dict
        """
        mod_obj = self.pool.get('ir.model.data')
        xml_data = self._get_datas(cursor, user, ids, context=context)
        month_quarter = xml_data['period'][:2]
        year = xml_data['period'][2:]
        data_file = ''

        # Can't we do this by etree?
        data_head = """<?xml version="1.0" encoding="ISO-8859-1"?>
<ns2:IntraConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/IntraConsignment" IntraListingsNbr="1">
    <ns2:Representative>
        <RepresentativeID identificationType="NVAT" issuedBy="%(issued_by)s">%(company_vat)s</RepresentativeID>
        <Name>%(company_name)s</Name>
        <Street>%(street)s</Street>
        <PostCode>%(post_code)s</PostCode>
        <City>%(city)s</City>
        <CountryCode>%(country)s</CountryCode>
        <EmailAddress>%(email)s</EmailAddress>
        <Phone>%(phone)s</Phone>
    </ns2:Representative>""" % (xml_data)
        if xml_data['mand_id']:
            data_head += '\n\t\t<ns2:RepresentativeReference>%(mand_id)s</ns2:RepresentativeReference>' % (xml_data)
        data_comp_period = '\n\t\t<ns2:Declarant>\n\t\t\t<VATNumber>%(vatnum)s</VATNumber>\n\t\t\t<Name>%(company_name)s</Name>\n\t\t\t<Street>%(street)s</Street>\n\t\t\t<PostCode>%(post_code)s</PostCode>\n\t\t\t<City>%(city)s</City>\n\t\t\t<CountryCode>%(country)s</CountryCode>\n\t\t\t<EmailAddress>%(email)s</EmailAddress>\n\t\t\t<Phone>%(phone)s</Phone>\n\t\t</ns2:Declarant>' % (xml_data)
        if month_quarter.startswith('3'):
            data_comp_period += '\n\t\t<ns2:Period>\n\t\t\t<ns2:Quarter>'+month_quarter[1]+'</ns2:Quarter> \n\t\t\t<ns2:Year>'+year+'</ns2:Year>\n\t\t</ns2:Period>'
        elif month_quarter.startswith('0') and month_quarter.endswith('0'):
            data_comp_period+= '\n\t\t<ns2:Period>\n\t\t\t<ns2:Year>'+year+'</ns2:Year>\n\t\t</ns2:Period>'
        else:
            data_comp_period += '\n\t\t<ns2:Period>\n\t\t\t<ns2:Month>'+month_quarter+'</ns2:Month> \n\t\t\t<ns2:Year>'+year+'</ns2:Year>\n\t\t</ns2:Period>'

        data_clientinfo = ''
        for client in xml_data['clientlist']:
            if not client['vatnum']:
                raise osv.except_osv(_('Data Insufficient!'),_('No vat number defined for %s') % client['partner_name'])
            data_clientinfo +='\n\t\t<ns2:IntraClient SequenceNumber="%(seq)s">\n\t\t\t<ns2:CompanyVATNumber issuedBy="%(country)s">%(vatnum)s</ns2:CompanyVATNumber>\n\t\t\t<ns2:Code>%(code)s</ns2:Code>\n\t\t\t<ns2:Amount>%(amount)s</ns2:Amount>\n\t\t</ns2:IntraClient>' % (client)

        data_decl = '\n\t<ns2:IntraListing SequenceNumber="1" ClientsNbr="%(clientnbr)s" DeclarantReference="%(dnum)s" AmountSum="%(amountsum)s">' % (xml_data)

        data_file += data_head + data_decl + data_comp_period + data_clientinfo + '\n\t\t<ns2:Comment>%(comments)s</ns2:Comment>\n\t</ns2:IntraListing>\n</ns2:IntraConsignment>' % (xml_data)
        context['file_save'] = data_file

        model_data_ids = mod_obj.search(cursor, user,[('model','=','ir.ui.view'),('name','=','view_vat_intra_save')], context=context)
        resource_id = mod_obj.read(cursor, user, model_data_ids, fields=['res_id'], context=context)[0]['res_id']

        return {
            'name': _('Save'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'partner.vat.intra',
            'views': [(resource_id,'form')],
            'view_id': 'view_vat_intra_save',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def preview(self, cr, uid, ids, context=None):
        xml_data = self._get_datas(cr, uid, ids, context=context)
        datas = {
             'ids': [],
             'model': 'partner.vat.intra',
             'form': xml_data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'partner.vat.intra.print',
            'datas': datas,
        }

partner_vat_intra()

class vat_intra_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(vat_intra_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })

report_sxw.report_sxw('report.partner.vat.intra.print', 'partner.vat.intra', 'addons/l10n_be/wizard/l10n_be_vat_intra_print.rml', parser=vat_intra_print, header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
