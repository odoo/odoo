#! -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Autores:
#	  Este software baseia-se no trabalho inicial de Paulino Ascenção <paulino1@sapo.pt> (l10n_pt_saft-6)
#    Adaptado à versão 7 por João Figueira<jjnf@communities.pt> e Jorge A. Ferreira <sysop.x0@gmail.com>
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

# Sysop
from __future__ import print_function

import datetime
#import tools
# import pooler
# from openerp import tools
# from cStringIO import StringIO
import base64
#import cStringIO
# import csv
#import pooler
#from osv import fields
#from osv import osv
from openerp import models, fields, api, _
#from tools.translate import _
#from xml.etree import ElementTree as et
from lxml import etree as et
#from xml.dom.minidom import parseString
import copy
from openerp import netsvc
#import netsvc
#logger = netsvc.Logger()
import logging
_logger = logging.getLogger(__name__)


##VALORES FIXO do cabecalho relativos ao OpenERP
productCompanyTaxID = '507477758'
productID =           'OpenERP/communities'
productVersion =      '8'
headerComment =       u'Software criado para a comunidade OpenERP Portugal'
softCertNr =          '0'

# Versao e codificação do xml
# xml_version = '<?xml version="1.0" encoding="windows-1252"?>'

class res_partner(models.Model):
    """Adiciona os campos requeridos pelo SAFT relativos a clientes e fornecedores:
    conservatória; numero do registo comercial; Indicadores da existencia de acordos de
    autofacturação para compras e vendas
    Torna o campo 'ref' obrigatorio e único e o 'vat' - NIF obrigatório"""
    _name = 'res.partner'
    _inherit = 'res.partner'

    # Só para os campos saft
    reg_com = fields.Char(string="N.Registo", size=32, help="Número do registo comercial")
    conservatoria = fields.Char(string="Conservatoria", size=64, help="Conservatória do registo comercial")

    # Adicionar campo 'indicador da existencia de acordos de 'auto-facturação' : 1 ou 0
    self_bill_sales = fields.Boolean(string="Sales: self-billing", help="Assinale se existe acordo de auto-facturação para as vendas a este parceiro")
    self_bill_purch = fields.Boolean(string="Purchases self-billing", help="Assinale se existe acordo de auto-facturação para as compras ao parceiro" )

# todo: permitir nas facturas de venda apenas parceiros clientes; Nãp permitir desmarcar campo 'cliente' se houver vendas.

class res_company(models.Model):
    _name = 'res.company'
    _inherit = 'res.company'

    open_journal = fields.Many2one(comodel_name="account.journal", string="Diário de Abertura", )


class account_tax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    country_region = fields.Selection(string="Espaço Fiscal", selection=[('PT', 'Continente'), ('PT-AC', 'Açores'), ('PT-MA', 'Madeira')], required=True, default="PT", )
    saft_tax_type = fields.Selection(string="Imposto", selection=[('IVA', 'IVA'), ('IS', 'Imp do Selo')], required=True, default="IVA", )
    saft_tax_code = fields.Selection(string="Nível de Taxa", selection=[('RED', 'Reduzida'), ('NOR', 'Normal'),('INT', 'Intermédia'), ('ISE', 'Isenta'), ('OUT', 'Outra')], required=True, default="NOR", )
    expiration_date = fields.Date(string="Data Expiração", )
    exemption_reason = fields.Char(string="Motivo da isenção", size=60, help="No caso de IVA isento, indique qual a norma do codigo do IVA que autribui a isenção")


class account_invoice(models.Model):
    """ Campos requeridos pelo saft:
            4.1.4.2. InvoiceStatus - ['N': Normal, 'A': Anulado, 'S':Auto-fact, 'F': Facturado(Talão de venda)]-calculado ao exportar
            4.1.4.3. Hash - assinatura (string 200)
            4.1.4.4. HashControl  Versão da chave (string 40)
            4.1.4.8. SelfBillingIndicator - indicador de auto-facturacao   - ler no diario relacionado com o "S" em 4.1.4.2
            4.1.4.14.13.2.  TaxCountryRegion - País ou Região do Imposto   -  todo: verificar novas regras da territorialidade no IVA
            4.1.4.14.13.5.  TaxAmount - Valor do imposto    - se tipo é ISelo
            4.1.4.14.14.    TaxExemptionReason - Motivo da isenção - o preceito legal aplicável - ler na tabela de impostos

    """
    _name = "account.invoice"
    _inherit = "account.invoice"

    hash = fields.Char(string="Assinatura", size=200, )
    hash_control = fields.Char(string="Chave", size=40, )
    system_entry_date = fields.Datetime(string="Data de confirmação", )
    write_date = fields.Datetime(string="Data de alteração", )

    def grosstotal(self, cr, uid,  inv_id):
        invoice = self.browse(cr, uid, inv_id)
        integer, decimal = str(invoice.amount_total).split('.')
        return '.'.join( [integer, decimal.ljust(2, '0')] )


class account_journal(models.Model):
    """ Adição de cmapos requeridos pelo saft:
    3.4.3.7  trasaction_type - para filtrar na contabilidade os tipos de transação conforme abaixo
    4.1.4.2/8  self_billing - servirá para preencher os campos 4.1.4.2 InvoiceStatus e 4.1.4.8 SelfBillingIndicator, nos casos de auto-facturação
    4.1.2.7    InvoiceType  classificar com um de FT, ND, NC  ou VD e AA alienação Acivos ou DA - devol activos
    """
    _name = "account.journal"
    _inherit = "account.journal"

    self_billing = fields.Boolean(string="Auto-Facturação", help='''Assinale, se este diário se destina a registar Auto-facturação.
            As facturas emitidas em substituição dos fornecedores, ao abrigo de acordos de auto-facturação, são assinaladas como tal no SAFT''')
    transaction_type = fields.Selection(string="Tipo de Lançamento", selection=[('N', 'Normal'), ('R', 'Regularizações'),('A', 'Apur. Resultados'), ('J', 'Ajustamentos')], help="Categorias para classificar os movimentos contabilísticos ao exportar o SAFT", default="N", )
    saft_inv_type = fields.Selection(string="Tipo de Documento", selection=[('FT', 'Factura'), ('ND', 'Nota de débito'),('NC', 'Nota de Crédito'), ('VD', 'Venda a Dinheiro'), ('AA', 'Alienação de Activos'), ('DA', 'Devolução de Activos')], required=False, help="Categorias para classificar os documentos comerciais, na exportação do SAFT", default="FT", )


class product_product(models.Model):
    _name = "product.product"
    _inherit = "product.product"

    _sql_constraints = [('code_unique','unique(default_code)', _("Product code must be unique!")),]

class account_invoice_line(models.Model):
    _name = "account.invoice.line"
    _inherit = "account.invoice.line"


def date_format(data, tipo='DateType'):
    d = datetime.datetime.strptime(data[:19], '%Y-%m-%d %H:%M:%S')
    if tipo == 'DateType':
        return d.strftime('%Y-%m-%d')
    else :
        return d.strftime('%Y-%m-%dT%H:%M:%S')


tipos_saft = [  ('C', 'Contabilidade'),                         # ctb na v.1
                ('F', u'Facturação'),                           # fact na v.1
                ('I', u'Integrado - Contabilidade e Facturação'), # int
                ('S', u'Autofacturação'),                         # novo v.2
                #('P', u'Dados parciais de facturação')        # nao implementado
              ]        # novo v.2


class wizard_saft(models.TransientModel):
    _name = "wizard.l10n_pt.saft"
    _rec_name = 'year'

    # def _default_company(self, cr, uid, context={}):
    def _default_company(self):
        """Devolve a companhia do utilizador, ou a primeira encontrada"""
        user = self.pool.get('res.users').browse(self._cr, self._uid, self._uid)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search([('parent_id', '=', False)])[0]

    # def _current_year(self, cr, uid, context={}):
    def _current_year(self):
        """ Devolve o ano mais recente existente na BD"""
        return self.pool.get('account.fiscalyear').search(self._cr, self._uid, [])[-1]

    def _default_period(self):
        """ Devolve período na BD"""
        ######## verificar
        ctx = dict(self._context or {}, account_period_prefer_normal=True)
        period_ids = self.pool.get('account.period').find(self._cr, self._uid, context=ctx)
        return period_ids[0]

    company_id = fields.Many2one(comodel_name="res.company", string="Companhia", required=True, default=_default_company, )
    tipo = fields.Selection(string="Tipo ficheiro", selection=tipos_saft, default="F", )
    year = fields.Many2one(comodel_name="account.fiscalyear", string="Exercício", required=True, default=_current_year, )
    filter_by = fields.Selection(string="Filter by", selection=[('d', 'Dates'), ('p', 'Periods'), ], required=True, default='d')
    date_end = fields.Date(string="Data final", default=fields.Date.context_today, )
    date_start = fields.Date(string="Data Inicial", default=fields.Date.context_today, )
    period_id = fields.Many2one(comodel_name="account.period", string="Periodo", default=_default_period, )


    @api.onchange('period_id')
    def onchange_period(self):
        if self.period_id:
            start_period = end_period = False
            self._cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               ORDER BY p.date_start ASC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (self.period_id.id, self.period_id.id))
            periods = [i[0] for i in self._cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            self.period_from= start_period
            self.period_to= end_period
        else:
            self.period_from=False
            self.period_to= False


    def act_cancel(self):
        #self.unlink(cr, uid, ids, context)
        return {'type':'ir.actions.act_window_close' }

    #def act_destroy(self, *args):
    def action_close(self, *args):
        return {'type':'ir.actions.act_window_close' }

    def getAddress(self, cr ,uid, ids, parent_tag, parent_id, add_type='default'):
        # obtem o primeiro id do tipo 'default' ou então o peimeiro id, do parceiro
        if add_type == 'default':
            cr.execute("SELECT id  FROM res_partner WHERE id = COALESCE( \
                 (SELECT MIN(id) FROM res_partner WHERE  id=%d AND type = '%s') , \
                 (SELECT MIN(id) FROM res_partner WHERE  id=%d ))" %(parent_id, add_type, parent_id))
            address_id = cr.fetchone()[0]
        else:
            cr.execute("SELECT id  FROM res_partner WHERE id = \
                 (SELECT MIN(id) FROM res_partner WHERE  id=%d AND type = '%s')" %(parent_id, add_type ))
            address_id = cr.fetchone()[0]


        # obtem os campos (para o id acima) de addressStruture
        cr.execute("SELECT ad.street||COALESCE(' '||ad.street2, ''), ad.city, ad.zip, c.code, r.name, \
                            COALESCE(ad.phone, ad.mobile), ad.fax, ad.email \
                    FROM res_partner ad \
                        LEFT JOIN res_country c ON c.id = ad.country_id \
                        LEFT JOIN res_country_state r ON r.id  = ad.state_id \
                    WHERE ad.id ="+ str(address_id) )
        street, city, postal_code, country_code, region, phone, fax, email = cr.fetchone()
        #print address
        # todo: criar aqui o XML do endereco
        """Funcao para gerar campo Address -   Elementos e ordem:
            BuildingNumber
            StreetName
          * AddressDetail
          * City
          * PostalCode
            Region
          * Country    """
        parent = et.Element( parent_tag )
        for el, txt in zip((  'AddressDetail', 'City', 'PostalCode', 'Region', 'Country'),
                             ( street, city, postal_code, region,  country_code)):
            if txt is None:
                if el == 'Country':
                    txt = 'PT'
                elif el == 'Region':
                    continue
                else:
                    txt = 'Desconhecido'
            i=et.SubElement(parent, el)
            i.text=unicode(txt)
            i.tail = '\n'
        phone_fax_mail = et.Element('PhoneFaxMail')
        for el, txt in zip( ('Telephone', 'Fax', 'Email'), (phone, fax, email)):
            if txt is None:
                continue
            et.SubElement(phone_fax_mail, el).text = unicode(txt)
        return  parent, phone_fax_mail
        #return address

    def action_extract_saft(self, cr, uid, ids, context=None):
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar o ficheiro xml SAFT ****')
        """Gera o conteudo do ficheiro xml 
        """

        self.this = self.browse(cr, uid, ids[0])
        #Namespaces declaration
        # Sysop
        self.xmlns = "urn:OECD:StandardAuditFile-Tax:PT_1.03_01"
        attrib={ 'xmlns': self.xmlns,
                 #'xmlns:xsi':"http://www.w3.org/2001/XMLSchema-instance",
                 #'xsi:noNamespaceSchemaLocation' : "saft-pt.xsd"
                 }

        root = et.Element("AuditFile", attrib = attrib )
        header = et.SubElement(root, 'Header', xmlns=self.xmlns)
        header.tail = '\n'
        #master
        root.append( self._get_masters(cr, uid, ids, context=context) )

        #entries : exclui na facturação
        if self.this.tipo in ('C', 'I'):
            root.append( self._get_entries() )
        #for el in (header, master, entries) :
        #    el.tail = '\n'
        
        # Sysop
        et.SubElement(header, 'AuditFileVersion').text='1.03_01'

        cr.execute("""
            SELECT p.id, p.vat, p.name, p.reg_com, p.conservatoria, p.website
            FROM res_partner p
            WHERE p.id = 1 """)

        p_id, vat, name, registo, conserv, web = cr.fetchone()

        for el, txt in zip(('CompanyID', 'TaxRegistrationNumber', 'TaxAccountingBasis',  'CompanyName'), (str(conserv)+' '+str(registo), vat and vat[2:] or None, self.this.tipo, name )):
            et.SubElement(header, el).text=txt
        # todo: Falta inserir o BusinessName (1.6), após o CompanyName  opcional
        compAddress, phone_fax_mail = self.getAddress(cr, uid, ids, 'CompanyAddress', p_id)
        
        header.append( compAddress )

        # le o ano fiscal na base de dados
        fy_obj = self.pool.get('account.fiscalyear')
        fy = fy_obj.browse(cr, uid, self.this.year.id)
        #### gera o header propriamente
        tags = (    ('FiscalYear',      fy.code,),
                    ('StartDate',       fy.date_start),
                    ('EndDate',         fy.date_stop),
                    ('CurrencyCode',    'EUR'),
                    ('DateCreated',     '%s' %str(datetime.datetime.now().strftime('%Y-%m-%d')) ),
                    ('TaxEntity',       'Sede'),
                    ('ProductCompanyTaxID',  productCompanyTaxID),   
                    ('SoftwareCertificateNumber', softCertNr),
                    ('ProductID',        productID),
                    ('ProductVersion',   productVersion),
                    ('HeaderComment',    headerComment),
                    )
        for tag, valor in tags:
            if valor is None :
                continue
            et.SubElement(header, tag).text=valor
        for element in phone_fax_mail.getchildren():
            header.append( element )
        del phone_fax_mail
        if web:
            et.SubElement(header,'Website').text = unicode(web)
        for element in header.getchildren():
            element.tail = '\n'

        #SourceDocumentos se tipo não é 'C'
        if self.this.tipo != 'C' :
            root.append( self._write_source_documents(cr, uid, fy.date_start, fy.date_stop) )

        xml_txt = et.tostring(root, encoding="windows-1252")
        out=base64.encodestring( xml_txt )   
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.l10n_pt.saft_result',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'context': {'default_saft_extracted':out},
            'target': 'new',
        }

    def _get_masters(self, cr, uid, ids, context=None):
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar MasterFiles')
#_logger.info('A exportar MasterFiles')
        master = et.Element('MasterFiles', xmlns=self.xmlns)
        master.tail='\n'
        # 2.1 GeneralLedger
        # obtem lista de contas com movimentos, com saldos de abertura
        # precisa obter contas-mãe para cada cta de movimento
        if self.this.tipo in ('C', 'I') :
            self._cr.execute("SELECT DISTINCT ac.id, ac.code, ac.name, ac.parent_id, COALESCE(debito, 0.0), COALESCE(credito, 0) \
                FROM account_move_line ml \
                    INNER JOIN account_account  ac  ON  ac.id = ml.account_id\
                    LEFT JOIN (SELECT account_id, SUM( debit) AS debito, SUM( credit ) AS credito\
                            FROM account_move_line WHERE journal_id = \
                            (SELECT open_journal FROM res_company WHERE id = "+str(self.this.comp.id)+") \
                            GROUP BY account_id)  abertura  ON  ml.account_id = abertura.account_id")
            acc_dict = {}
            acc_obj = self.pool.get('account.account')
            for ac_id, code, name, parent, debit, credit in cr.fetchall():
                #print code, name, parent, debit, credit
                acc_dict[ code ] = {'name':name, 'debit':debit, 'credit':credit}
                account = acc_obj.browse(parent )
                while account :
                    if len(account.code) < 2 :
                        break
                    try :
                        acc_dict[account.code]['debit']  += debit
                        acc_dict[account.code]['credit'] += credit
                    except KeyError :
                        acc_dict[account.code] = {'name':account.name, 'debit':debit, 'credit':credit}
                    account = account.parent_id

#            logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar Plano de Contas (GeneralLedger)')
#_logger.info('A exportar tabela de contas (GeneralLedger)')
            for code in sorted( acc_dict ):
                gl = et.SubElement(master, 'GeneralLedger')
                gl.tail='\n'
                et.SubElement(gl, 'AccountID').text=code
                et.SubElement(gl, 'AccountDescription').text = acc_dict[code]['name']#.decode('utf8')
                et.SubElement(gl, 'OpeningDebitBalance').text= str( acc_dict[code]['debit'] )
                et.SubElement(gl, 'OpeningCreditBalance').text= str( acc_dict[code]['credit'] )
                for element in gl.getchildren():
                    element.tail='\n'

        ####   2.2 Customer    ========================================================================
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar Clientes')
#_logger.info('A exportar Clientes')
        self._write_partners(cr, uid, ids, master)

        ####   2.3 Supplier  =========================================
        if self.this.tipo in ('C', 'I'):
#            logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar Fornecedores')
#_logger.info('A exportar Fornecedores')
            self._write_partners(self._cr, self._uid, self.ids, master, partner_role='Supplier')
            
        # 2.4 Product   -   Não entra no tipo 'C'
        if self.this.tipo != 'C' :
            self._write_products(cr, uid, ids,master)

        # 2.5 TaxTable
        master.append( self._get_taxes(cr, uid, ids, context=context) )
        return master
        
        
    def _write_partners(self, cr, uid, ids, master, partner_role='Customer'):
        """ Exporta os elementos 2.2 Customer e 2.3 Supplier
         1 CustomerID (Supplier)      * partner.id | partner.ref
         2 AccountID                 * ler em properties ???
         3 CustomerTaxID (Supplier)   * partner.vat
         4 CompanyName                * partner.name
         5 Contact       (Opcional)    [address.name (default)]
         6 BillingAddress             * address[invoice|default]
         7 ShipToAddress  (From)        address[delivery]
         8 Telephone                    address[default].phone | mobile
         9 Fax                          address[default].fax
        10 Email                        address[default].email
        11 Website                      partner.website
        12 SelfBillingIndicator """
        
        condition = [('active', '=', 'True')]
        if partner_role == 'Customer':
            condition.append( ('customer', '=', 'True') )
            #ship_add = 'To'
        elif partner_role == 'Supplier':
            condition.append( ('supplier', '=', 'True') )
            #ship_add = 'From'
        else:
            return
            
        partner_obj = self.pool.get('res.partner')
        partner_ids = partner_obj.search(cr, uid, condition, order='id')
        partners = partner_obj.browse(cr, uid, partner_ids)
        for partner in partners:
            if partner_role == 'Customer':
                accountId= unicode(partner.property_account_receivable.code)
                self_bill= unicode(partner.self_bill_sales and '1' or '0')
            else:
                accountId= unicode(partner.property_account_payable.code)
                self_bill= unicode(partner.self_bill_purch and '1' or '0')

            partner_element = et.SubElement(master, partner_role)
            #.1  ID
            et.SubElement(partner_element, '%sID'%partner_role).text = unicode(partner.id)
            et.SubElement(partner_element, 'AccountID').text = accountId 
            et.SubElement(partner_element, '%sTaxID'%partner_role).text = unicode(partner.vat and partner.vat[2:] or '')
            #.4  CompanyName
            et.SubElement(partner_element, 'CompanyName').text = unicode(partner.name)
            #.5 Contact   - Opcional  

            #.6  BillingAddress
            billingAddress, phone_fax_mail = self.getAddress(cr, uid, ids, 'BillingAddress', partner.id)
            partner_element.append( billingAddress )
            # todo: .7 Ship[To|From]Address   
            #8-9-10  elementos facultativos no OpenERP constam do endereço, no saft estão fora.
            for element in phone_fax_mail:
                partner_element.append( element )
            #.11 Website
            if partner.website:
                et.SubElement(partner_element, 'Website').text = unicode(partner.website)
            et.SubElement(partner_element, 'SelfBillingIndicator').text = self_bill
            partner_element.tail='\n'


    def _write_products(self, cr, uid, ids, master):
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar tabela de produtos')
#_logger.info('A exportar tabela de produtos')
        ids = self.pool.get('product.product').search(cr, uid, [])
        products = self.pool.get('product.product').browse(cr, uid, ids)

        for product in products:
            eproduct = et.SubElement(master, "Product")
            eproduct.tail='\t    '
            eproduct_type = et.SubElement(eproduct, "ProductType")
            if product.type == 'product':
                eproduct_type.text = 'P'
            elif product.type == 'service':
                eproduct_type.text = 'S'
            else:
                eproduct_type.text = 'O'
            eproduct_code = et.SubElement(eproduct, "ProductCode")
            eproduct_code.text = unicode(product.default_code)
            eproduct_group = et.SubElement(eproduct, "ProductGroup")
            eproduct_group.text = product.categ_id.name

            eproduct_description = et.SubElement(eproduct, "ProductDescription")
            eproduct_description.text = product.name

            eproduct_number_code = et.SubElement(eproduct, "ProductNumberCode")
            if product.ean13:
                eproduct_number_code.text = unicode(product.ean13)
            else:
                eproduct_number_code.text = unicode(product.default_code)

    def _get_taxes(self, cr, uid, ids, context=None):
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar TaxTable')
#_logger.info('A exportar TaxTable')
        taxTable = et.Element('TaxTable')
        cr.execute("SELECT DISTINCT saft_tax_type, country_region, saft_tax_code, name, expiration_date, type, amount \
                    FROM account_tax WHERE parent_id is NULL \
                    ORDER BY country_region, amount")

        for TaxType, region, TaxCode, Description, Expiration, tipo, valor in cr.fetchall():
            taxTableEntry = et.SubElement(taxTable, 'TaxTableEntry')
            et.SubElement(taxTableEntry, 'TaxType').text = TaxType
            et.SubElement(taxTableEntry, 'TaxCountryRegion').text = region
            et.SubElement(taxTableEntry, 'TaxCode').text = TaxCode
            et.SubElement(taxTableEntry, 'Description').text = Description
            if Expiration is not None:
                et.SubElement(taxTableEntry, 'TaxExpirationDate').text = Expiration     # opcional
            if tipo == 'percent':
                et.SubElement(taxTableEntry, 'TaxPercentage').text = str(valor)
            else:
                # sysop ToDo - amount: verify where it comes from; quick fix
                # et.SubElement(taxTableEntry, 'TaxAmount').text = str(amount)
                et.SubElement(taxTableEntry, 'TaxAmount').text = str(valor)
        return taxTable


    def _get_entries(self, cr, uid, ids, context=None):
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar movimentos da contabilidade')
#_logger.info('... a exportar movimentos da contabilidade')
        # 3. GeneralLedgerEntries
        entries = et.Element('GeneralLedgerEntries', xmlns=self.xmlns)
        entries.tail='\n'
        # 3.1 NumberOfEntries
        numberOfEntries = et.SubElement(entries, 'NumberOfEntries')
        num_entries = 0
        # 3.2 TotalDebit
        totalDebit = et.SubElement(entries, 'TotalDebit')
        total_debit = 0
        # 3.3 TotalCredit
        totalCredit = et.SubElement(entries, 'TotalCredit')
        total_credit = 0
        # dict para reunir id das contas com movimentos
        #self.acc_ids={}

        # obtem diarios excepto diario de abertura
        if not self.this.comp.open_journal :
            raise osv.except_osv(_('Error !'), _(u'Falta definir o diário de abertura da companhia'))
        
        cr.execute( " SELECT DISTINCT j.id, j.code, j.name, j.type, j.transaction_type \
                      FROM account_journal_period ajp INNER JOIN account_journal j ON ajp.journal_id = j.id \
                      WHERE j.id <>" + str(self.this.comp.open_journal.id)+ " AND ajp.period_id IN \
                                      (SELECT id FROM account_period WHERE fiscalyear_id = "+str(self.this.year.id)+")" )
        journals = cr.fetchall()
        for j_id, j_code, j_name, j_type, transaction_type in journals:
            # 3.4 Journal
            ejournal = et.SubElement(entries, 'Journal')
            # 3.4.1  JournalID   and   3.4.2 Description
            et.SubElement(ejournal, 'JournalID').text = j_code
            et.SubElement(ejournal, 'Description').text = j_name

            # transaccoes do diario e exercicio
            cr.execute("\
                SELECT m.id, m.name, p.code, m.date, COALESCE( uc.login, uw.login), m.ref,\
                    COALESCE(m.write_date, m.create_date)\
                FROM account_move m \
                    INNER JOIN account_period p ON m.period_id = p.id\
                    LEFT JOIN res_users uc ON uc.id = m.create_uid\
                    LEFT JOIN res_users uw ON uw.id = m.write_uid\
                WHERE m.period_id IN (SELECT id FROM account_period \
                                      WHERE fiscalyear_id = "+str(self.this.year.id) +")\
                      AND m.state = 'posted' AND m.journal_id = " + str(j_id) + "\
                ORDER BY m.name")
            journal_transactions = cr.fetchall()
            for move_id, trans_id, period, date, user, desc, post_date in journal_transactions:
                num_entries += 1
                # 3.4.3   Transaction
                self.transactionID = unicode(date+' '+trans_id.replace('/', ' '))
                trans_el = et.SubElement(ejournal, 'Transaction')
                et.SubElement(trans_el, 'TransactionID').text = self.transactionID
                et.SubElement(trans_el, 'Period').text = period
                et.SubElement(trans_el, 'TransactionDate').text = date
                et.SubElement(trans_el, 'SourceID').text = unicode(user)
                et.SubElement(trans_el, 'Description').text = unicode(desc)
                
                # 3.4.3.6 DocArchivalNumber
                et.SubElement(trans_el, 'DocArchivalNumber').text = unicode(trans_id.split('/')[1] )
                # todo: 3.4.3.7 TransactionType   - campo account_journal.transaction_type
                et.SubElement(trans_el, 'TransactionType').text = unicode(transaction_type)
                # 3.4.3.8 GLPostingDate  data no formata AAAA-MM-DD Thh:mm:ss 
                #if isinstance(post_date, str) : print move_id, post_date
                et.SubElement(trans_el, 'GLPostingDate').text = date_format(post_date, 'DateTimeType')
                # 3.4.3.9|10  CustomerID|SupllierID  se diario é de vendas  - clientes ; se compras : fornecedores
                # usa o id interno para referenciar parceiros  ????
                if j_type == 'sale':
                    partner_el = et.SubElement(trans_el, 'CustomerID')
                elif j_type == 'purchase':
                    partner_el = et.SubElement(trans_el, 'SupplierID')
                    
                # 3.4.3.11 Line   Adiciona linhas dos movimentos
                cr.execute("SELECT l.id, a.id, a.code, l.ref, COALESCE(l.write_date, l.create_date), \
                                    l.name, l.debit, l.credit, l.partner_id \
                        FROM account_move_line l\
                            INNER JOIN account_account a ON l.account_id = a.id\
                        WHERE l.move_id = "+str(move_id) +
                        " ORDER BY l.id")

                # Assumir que em documentos de venda e de compra o parceiro é o mesmo em todas as linhas
                for line, acc_id, acc_code, source, date, ldesc, debit, credit, partner in cr.fetchall():
                    line_el = et.SubElement(trans_el, 'Line')
                    # 3.4.3.11.1  RecordID  - usa o id interno da tabela account_line
                    et.SubElement(line_el, 'RecordID').text=str(line)
                    et.SubElement(line_el, 'AccountID').text=acc_code
                    et.SubElement(line_el, 'SystemEntryDate').text= date_format( date, 'DateTimeType')
                    et.SubElement(line_el, 'Description').text=ldesc
                    if debit :
                        et.SubElement(line_el, 'DebitAmount').text=str(debit)
                        total_debit += debit
                    elif credit :
                        et.SubElement(line_el, 'CreditAmount').text=str(credit)
                        total_credit += credit
                    # /Line
                    for element in line_el.getchildren():
                        element.tail='\n                '
                if j_type in ('sale', 'purchase'):
                    partner_el.text = str(partner)
                for element in trans_el.getchildren():
                    element.tail='\n            '
            for element in ejournal.getchildren():
                element.tail='\n        '
        numberOfEntries.text = str(num_entries)
        totalDebit.text = str(total_debit)
        totalCredit.text = str(total_credit)
        for element in entries.getchildren():
            element.tail = '\n    '
        return entries

    def _write_invoice(self, cr, uid, invoice, eparent):
        # elemento 4.1.4 Invoice
        # 4.1.4.1
        et.SubElement(eparent, u"InvoiceNo").text = unicode(invoice.journal_id.saft_inv_type+' '+invoice.number)

        edoc_status = et.SubElement(eparent, u"DocumentStatus")
        
        # 4.1.4.2 - InvoiceStatus
        if invoice.state == 'cancel':
            status_code = 'A'
        elif invoice.journal_id.self_billing is True:
            status_code = 'S'
        else:
            status_code = 'N'
        et.SubElement(edoc_status, u"InvoiceStatus").text = unicode(status_code)
        et.SubElement(edoc_status, u"InvoiceStatusDate").text = date_format( invoice.system_entry_date or invoice.write_date, 'DateTimeType')
        et.SubElement(edoc_status, u"SourceID").text = unicode(invoice.user_id.login)
        et.SubElement(edoc_status, u"SourceBilling").text = 'P'        
        # 4.1.4.3 - Hash
        et.SubElement(eparent, u"Hash").text = unicode(invoice.hash)
        # 4.1.4.4 - HasControl
        et.SubElement(eparent, u"HashControl").text = unicode(invoice.hash_control)
        # 4.1.4.5 - Period          # todo: period name
        et.SubElement(eparent, u"Period").text = unicode(invoice.period_id.code)
        # 4.1.4.6  InvoiceDate
        et.SubElement(eparent, u"InvoiceDate").text = unicode(invoice.date_invoice)
        # 4.1.4.7 InvoiceType
        et.SubElement(eparent, u"InvoiceType").text = invoice.journal_id.saft_inv_type
        # 4.1.4.8  SelfBillingIndicator
        regime_special = et.SubElement(eparent, u"SpecialRegimes")

        et.SubElement(regime_special, "SelfBillingIndicator").text = str(invoice.journal_id.self_billing and '1' or '0')
        #Indicador da existência de adesão ao regime de IVA de Caixa. Deve ser preenchido com 1 se houver adesão e com 0 (zero) no caso contrário.
        et.SubElement(regime_special, u"CashVATSchemeIndicator").text = '0'
        #Deve ser preenchido com 1 se respeitar a faturação emitida em nome e por conta de terceiros e com 0 (zero) no caso contrário.
        et.SubElement(regime_special, u"ThirdPartiesBillingIndicator").text = '0'
        et.SubElement(eparent, u"SourceID").text = unicode(invoice.user_id.login)
        # 4.1.4.9  SystemEntryDate
        # provisorio enquanto a certificação não funciona, le o write_date
        et.SubElement(eparent, u"SystemEntryDate").text = date_format( invoice.system_entry_date or invoice.write_date, 'DateTimeType')
        # 4.1.4.10 TransactioID - apenas no caso de ficheiro integrado
        if self.this.tipo == 'I':
            eTransactionID = et.SubElement(eparent, "TransactionID")
            if invoice.state == 'cancel':
                eTransactionID.text = 'Anulado'
            else:
                eTransactionID.text = self.transactionID
        # 4.1.4.11 CustomerID
        et.SubElement(eparent, u"CustomerID").text = unicode(invoice.partner_id.id)


    def _write_source_documents(self, cr, uid, start_date, final_date):
        esource_documents = et.Element('SourceDocuments')
#        logger.notifyChannel("saft :", netsvc.LOG_INFO, ' A exportar Source Documents')
#_logger.info('A exportar Source Documents')
        # todo: verificar facturas no estado 'cancel' que nao passaram pelo estado 'open'. devem se excluidas
        #       neste caso nao tem numero interno preenchido
        # criterios de selecao das facturas:
        args = [('date_invoice', '>=', start_date), ('date_invoice', '<=', final_date), 
                ('state', 'in', ['open', 'paid'])
                ]
        if self.this.tipo == 'S':
            args.append( ('type', 'in',["in_invoice","in_refund"]) )
            args.append( ('journal_id.self_billing', '=', "True") )
            #args.append( ('partner_id' '=', self.this.partner_id))
        else :  
            args.append( ('type', 'in',["out_invoice","out_refund"]) ) 
            #args.append( ('journal_id.self_billing', '=', "False") )
        invoice_obj = self.pool.get('account.invoice')
        ids = invoice_obj.search(cr, uid, args, order='internal_number')
        invoices = invoice_obj.browse(cr, uid, ids)

        esales_invoices = et.SubElement(esource_documents, "SalesInvoices")

        # totals
        enumber_of_entries = et.SubElement(esales_invoices, u"NumberOfEntries")
        etotal_debit = et.SubElement(esales_invoices, u"TotalDebit")
        etotal_credit = et.SubElement(esales_invoices, u"TotalCredit")
        enumber_of_entries.text = str(len(ids))
        total_debit = 0
        total_credit = 0

        # Invoice
        for invoice in invoices:
            # 4.1.4   Invoice
            einvoice = et.SubElement(esales_invoices, u"Invoice")
            self._write_invoice(cr, uid, invoice, einvoice)

            ## 4.1.4.12  ShipTo local e data da entrega
            #eship_to = et.SubElement(einvoice, u"ShipTo")
            # todo: deliveryID and date
            # edelivery_id = et.SubElement(eship_to, u"DeliveryID")
            # edelivery_date = et.SubElement(eship_to, u"DeliveryDate")
            #edelivery_id.text = ''
            # data da factura usada como data da entrega
            # edelivery_date.text = invoice.date_invoice

            ## Delivery address
            #ship_address, phone_fax = self.getAddress( cr, uid, 'Address', invoice.partner_id.id, add_type='delivery') 
            #eship_to.append( ship_address)

            ## 4.1.4.13  ShipFrom  Local e data de saida dos artigos
            #eship_from = et.SubElement(einvoice, u"ShipFrom")
            ## todo: deliveryID and date
            #edelivery_id = et.SubElement(eship_from, u"DeliveryID")
            #edelivery_date = et.SubElement(eship_from, u"DeliveryDate")
            #edelivery_id.text = ''
            # Data da entrega igual à da factura
            #edelivery_date.text =  unicode(invoice.date_invoice)
            ## 4.1.4.13.3  address


            # 4.1.4.14  Line
            line_no = 1
            for line in invoice.invoice_line:
                eline = et.SubElement(einvoice, u"Line")
                # 4.1.4.14.1  LineNumber
                et.SubElement(eline, u"LineNumber").text = unicode(line_no)
                line_no+= 1

                # 4.1.4.14.2  OrderReferences  todo: (optional) referencia à encomenda do cliente
                #eorder_references = et.SubElement(eline, u"OrderReferences")
                #eoriginating_on = et.SubElement(eorder_references, u"OriginatingON")
                #eorder_date = et.SubElement(eorder_references, u"OrderDate")
                #eoriginating_on.text = ''
                #eorder_date.text = ''

                # 4.1.4.14.3 ProductCode and 4.1.4.14.4 Description
                if line.product_id:
                    et.SubElement(eline, u"ProductCode").text = unicode(line.product_id.default_code)
                et.SubElement(eline, u"ProductDescription").text = unicode(line.product_id and line.product_id.name or line.name)
                
                # 4.1.4.14.5  Quantity
                et.SubElement(eline, u"Quantity").text = unicode(line.quantity)
                # 4.1.4.14.6  UnitOfMeasure
                if line.uos_id : # unit of measure (optional)
                    et.SubElement(eline, u"UnitOfMeasure").text=line.uos_id.name
                # 4.1.4.14.7  UnitPrice
                if line.price_unit:
                    et.SubElement(eline, u"UnitPrice").text = unicode(line.price_unit)
                if line.price_unit and line.quantity:
                    amount = line.price_unit * line.quantity

                # todo: TaxPointDate - data do acto gerador do imposto - da entrega ou prestação do serviço
                # usar data da guia de remessa, igual à data usada em ShipTo/DeliveryDate
                et.SubElement(eline, u"TaxPointDate").text = invoice.date_invoice

                ## todo: 4.1.4.14.9 References (optional)
                #ereferences = et.SubElement(eline, u"References")
                ## todo: 4.1.4.14.9.1 CreditNote
                #ecredit_note = et.SubElement(ereferences, u"CreditNote")
                #et.SubElement(ecredit_note, u"Reference")
                #et.SubElement(ecredit_note, u"Reason")
                
                # 4.1.4.14.10  Description
                et.SubElement(eline, u"Description").text = line.name

                # debit and credit amount
                debit_amount = credit_amount = 0
                # 4.1.4.14.11**  DebitAmount
                if invoice.type == 'out_refund':
                    et.SubElement(eline, u"DebitAmount").text = unicode(amount)
                    total_debit += amount
                # 4.1.4.14.12**  CreditAmount
                elif invoice.type == 'out_invoice' :
                    et.SubElement(eline, u"CreditAmount").text = unicode(amount)
                    total_credit += amount

                # Impostos
                for tax in line.invoice_line_tax_id:
                    # 4.1.4.14.13 Tax   see invoice_line_tax (optional)
                    etax = et.SubElement(eline, u"Tax")
                    # 4.1.4.14.13.1 TaxType
                    et.SubElement(etax, u"TaxType").text = unicode(tax.saft_tax_type)
                    # 4.1.4.14.13.2  TaxCountryRegion
                    et.SubElement(etax, u"TaxCountryRegion").text = unicode(tax.country_region)
                    # 4.1.4.14.13.3  TaxCode
                    et.SubElement(etax, u"TaxCode").text = unicode(tax.saft_tax_code)
                    # 4.1.4.14.13.4**  TaxPercentage ou 4.1.4.14.13.5** TaxAmount
                    if   tax.type == 'percent':
                        et.SubElement(etax, u"TaxPercentage").text = str( tax.amount )
                    elif tax.type == 'fixed' :
                        et.SubElement(etax, u"TaxPercentage").text = str( tax.amount )
                # 4.1.4.14.14**    ExemptionReason - obrigatorio se TaxPercent e TaxAmount ambos zero
                if line.invoice_line_tax_id: 
                    if tax.saft_tax_type == 'IVA' and tax.amount == 0.0:
                        et.SubElement(etax, u"TaxExemptionReason").text = unicode(tax.exemption_reason)

                # 4.1.4.14.15  SettlementAmount (optional) - valor do desconto da linha
                et.SubElement(eline, u"SettlementAmount").text = str(line.discount )
                # /line

            # document totals
            edocument_totals = et.SubElement(einvoice, u"DocumentTotals")
            etax_payable = et.SubElement(edocument_totals, u"TaxPayable")
            enet_total = et.SubElement(edocument_totals, u"NetTotal")
            egross_total = et.SubElement(edocument_totals, u"GrossTotal")

            etax_payable.text = invoice.amount_tax and unicode(invoice.amount_tax) or '0.0'
            enet_total.text = invoice.amount_untaxed and unicode(invoice.amount_untaxed) or '0.0'
            egross_total.text = invoice_obj.grosstotal(cr, uid, invoice.id)
            # TODO currency : only in case of foreign currency (optional)
            if invoice.currency_id.name != 'EUR':
                ecurrency = et.SubElement(edocument_totals, u"Currency")
                ecurrency_name = et.SubElement(ecurrency, u"CurrencyCode")
                #ecurrency_credit_amount = et.SubElement(ecurrency, u"CurrencyCreditAmount")
                #ecurrency_debit_amount = et.SubElement(ecurrency, u"CurrencyDebitAmount")
                ecurrency_name.text = invoice.currency_id.name
                #ecurrency_credit_amount.text = ''
                #ecurrency_debit_amount.text = ''

            # TODO: settlement (optional)
            #esettlement = et.SubElement(edocument_totals, u"Settlement")
            #esettlement_discount = et.SubElement(esettlement, u"SettlementDiscount")
            #esettlement_amount = et.SubElement(esettlement, u"SettlementAmount")
            #esettlement_date = et.SubElement(esettlement, u"SettlementDate")
            #epayment_mechanism = et.SubElement(esettlement, u"PaymentMechanism")
            #esettlement_discount.text = ''
            #esettlement_amount.text = ''
            #esettlement_date.text = ''
            #epayment_mechanism.text = ''

        # totals
        etotal_debit.text = unicode(total_debit)
        etotal_credit.text = unicode(total_credit)
        return esource_documents


class wizard_saft_result(models.TransientModel):

    _name = "wizard.l10n_pt.saft_result"
    _rec_name = 'file_name'

    file_name = fields.Char(string='Nome do ficheiro', default="saft_pt.xml")
    saft_extracted = fields.Binary('SAFT-PT')
    
    def action_close(self, *args):
        return {'type':'ir.actions.act_window_close' }    
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

