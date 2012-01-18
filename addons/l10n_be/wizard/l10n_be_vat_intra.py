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
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', domain=[('parent_id', '=', False)]),
        'test_xml': fields.boolean('Test XML file', help="Sets the XML output as test file"),
        'mand_id' : fields.char('MandataireId', size=14, required=True,  help="This identifies the representative of the sending company. This is a string of 14 characters"),
        'msg': fields.text('File created', size=14, readonly=True),
        'no_vat': fields.text('Partner With No VAT', size=14, readonly=True, help="The Partner whose VAT number is not defined they doesn't include in XML File."),
        'file_save' : fields.binary('Save File', readonly=True),
        'country_ids': fields.many2many('res.country', 'vat_country_rel', 'vat_id', 'country_id', 'European Countries'),
        }

    _defaults = {
        'country_ids': _get_europe_country,
        'file_save': _get_xml_data,
        'name': 'vat_Intra.xml',
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
        post_code = street = city = country = p_list = data_clientinfo = ''
        seq = amount_sum = 0

        wiz_data = self.browse(cr, uid, ids[0], context=context)

        if wiz_data.tax_code_id:
            data_cmpny = wiz_data.tax_code_id.company_id
        else:
            data_cmpny = obj_user.browse(cr, uid, uid, context=context).company_id

        # Get Company vat
        company_vat = data_cmpny.partner_id.vat
        if not company_vat:
            raise osv.except_osv(_('Data Insufficient'),_('No VAT Number Associated with Main Company!'))
        company_vat = company_vat.replace(' ','').upper()

        if len(wiz_data.period_code) != 6:
            raise osv.except_osv(_('Wrong Period Code'), _('The period code you entered is not valid.'))

        if not wiz_data.period_ids:
            raise osv.except_osv(_('Data Insufficient!'),_('Please select at least one Period.'))

        p_id_list = obj_partner.search(cr, uid, [('vat','!=',False)], context=context)
        if not p_id_list:
            raise osv.except_osv(_('Data Insufficient!'),_('No partner has a VAT Number asociated with him.'))

        seq_controlref = obj_sequence.get(cr, uid, 'controlref')
        seq_declarantnum = obj_sequence.get(cr, uid, 'declarantnum')
        cref = company_vat[2:] + seq_controlref[-4:]
        dnum = cref + seq_declarantnum[-5:]

        addr = obj_partner.address_get(cr, uid, [data_cmpny.partner_id.id], ['invoice'])
        email = data_cmpny.partner_id.email
        phone = data_cmpny.partner_id.phone
        if email == False:
            email = ''
        if phone == False:
            phone = ''

        if addr.get('invoice',False):
            ads = obj_partner_add.browse(cr, uid, [addr['invoice']])[0]
            city = (ads.city or '')
            post_code = (ads.zip or '')
            if city == ' ':
                city = ''
            if post_code == ' ':
                post_code = ''
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ' '
                street += ads.street2
            if ads.country_id:
                country = ads.country_id.code

        xmldict.update({
                        'company_name': data_cmpny.name,
                        'company_vat': company_vat, 
                        'vatnum':  company_vat[2:],
                        'controlref': seq_controlref,
                        'cref': cref, 
                        'mand_id': wiz_data.mand_id, 
                        'sender_date': str(time.strftime('%Y-%m-%d')),
                        'street': street,
                        'city': city,
                        'post_code': post_code,
                        'country': country,
                        'email': email,
                        'phone': phone,
                        'period': wiz_data.period_code,
                        'clientlist': []
                        })
        
        codes = ('44', '46L', '46T')
        cr.execute('''SELECT p.name As partner_name, l.partner_id AS partner_id, p.vat AS vat, t.code AS intra_code, SUM(l.tax_amount) AS amount
                      FROM account_move_line l
                      LEFT JOIN account_tax_code t ON (l.tax_code_id = t.id)
                      LEFT JOIN res_partner p ON (l.partner_id = p.id)
                      WHERE t.code IN %s
                       AND l.period_id IN %s
                      GROUP BY p.name, l.partner_id, p.vat, t.code''', (codes, tuple([p.id for p in wiz_data.period_ids])))            

        p_count = 0
        for row in cr.dictfetchall():
            if not row['vat']:
                p_list += str(row['partner_name']) + ', '
                p_count += 1
                continue

            seq += 1
            amt = row['amount'] or 0
            amt = int(round(amt * 100))
            amount_sum += amt

            intra_code = row['intra_code'] == '44' and 'S' or (row['intra_code'] == '46L' and 'L' or (row['intra_code'] == '46T' and 'T' or ''))
#            intra_code = row['intra_code'] == '88' and 'L' or (row['intra_code'] == '44b' and 'T' or (row['intra_code'] == '44a' and 'S' or ''))

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
        for country in xml_data['clientlist']:
            if country['country'] == 'BE':
                country['country'] = ''
            else:
                country['country'] = country['country']

        # Can't we do this by etree?
        data_head = """<?xml version="1.0"?>
<IntraConsignment xmlns="http://www.minfin.fgov.be/IntraConsignment" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" RecipientId="VAT-ADMIN" SenderId="%(company_vat)s" ControlRef="%(controlref)s" IntraListingsNbr="%(mand_id)s" SenderDate="%(sender_date)s" VersionTech="1.3">
	<Representative>%(company_name)s</Representative>
	<RepresentativeReference>%(mand_id)s</RepresentativeReference>""" % (xml_data)
    
        data_comp_period = '\n\t\t<Declarant>\n\t\t\t<VATNumber xmlns="http://www.minfin.fgov.be/InputCommon">%(vatnum)s</VATNumber>\n\t\t\t<Name>%(company_name)s</Name>\n\t\t\t<Street>%(street)s</Street>\n\t\t\t<PostCode>%(post_code)s</PostCode>\n\t\t\t<City>%(city)s</City>\n\t\t\t<CountryCode>%(country)s</CountryCode>\n\t\t<EmailAddress>%(email)s</EmailAddress>\n\t\t<Phone>%(phone)s</Phone></Declarant>' % (xml_data)
        if month_quarter.startswith('3'):
            data_comp_period += '\n\t\t<Period>\n\t<Quarter>'+month_quarter+'</Quarter> \n\t<Year>'+year+'</Year></Period>'
        elif month_quarter.startswith('0') and month_quarter.endswith('0'):
            data_comp_period+= '\n\t\t<Period>%(period)s</Period>' % (xml_data)
        else:
            data_comp_period += '\n\t\t<Period>\n\t<Month>'+month_quarter+'</Month> \n\t<Year>'+year+'</Year></Period>'

        data_clientinfo = ''
        for client in xml_data['clientlist']:
            data_clientinfo +='\n\t\t<IntraClient SequenceNumber="%(seq)s">\n\t\t\t<CompanyVATNumber issuedBy="%(country)s">%(vatnum)s</CompanyVATNumber>\n\t\t\t<Code>%(code)s</Code>\n\t\t\t<Amount>%(amount)s</Amount>\n\t\t\n\t\t<CorrectingPeriod></CorrectingPeriod></IntraClient>' % (client)

        data_decl = '\n\t<IntraListing SequenceNumber="1" ClientsNbr="%(clientnbr)s" DeclarantReference="%(dnum)s" AmountSum="%(amountsum)s" >' % (xml_data)

        data_file += data_head + data_decl + data_comp_period + data_clientinfo + '\n<FileAttachment></FileAttachment>\n<Comment></Comment>\n\t</IntraListing>\n</IntraConsignment>'
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
        
report_sxw.report_sxw('report.partner.vat.intra.print', 'partner.vat.intra', 'addons/l10n_be/wizard/l10n_be_vat_intra_print.rml', parser=vat_intra_print)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
