##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
import pooler
from report import report_sxw

class account_tax_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_tax_report, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_invoice': self.getInvoices,
            'add_invoice': self.addInvoice,
            'get_tax': self.getTax,
            'get_tax_detail' : self.getTaxDetail,
            'get_retail' : self.getRetailTax,
            'get_retail_detail' : self.getRetailTaxDetail,
            'get_local_sale' : self.getLocalSale,
            'get_retail_sale' : self.getRetailSale,
            'total_local_sale' : self.getTotalLocalSale,
            'total_local_tax' : self.getTotalLocalTax,
            'total_retail_sale' : self.getTotalRetailSale,
            'total_retail_tax' : self.getTotalRetailTax,
            'time': time,
            'get_period': self.getPeriod,
            'test' : self.testMethod,
            
        })
        self.local = 0
        self. retail = 0
        
        self.tax_tax = {}
        self.retail_tax = {}
        
        self.sale_tax = {}
        self.sale_retail = {}
        
        self.total_local_sale = 0
        self.total_local_tax = 0
        
        self.total_retail_sale = 0
        self.total_retail_tax = 0
        
        self.invoices = []
        self.flag = False
    #end def
    
    def getPeriod(self, period_id):
        return self.pool.get('account.period').browse(self.cr, self.uid, period_id).name
    #end def
    
    def testMethod(self, obj):
        print type(obj) == type({}), obj;
        if type(obj) == type({}) and not self.flag:
            if obj.has_key('form'):
                self.flag = True
                ids = self.pool.get('account.move.line').search(self.cr, self.uid, [('period_id','=',obj['form']['period_id'])])
                account = self.pool.get('account.move.line').read(self.cr, self.uid,ids,['invoice'])
                invoice_ids = []
                for i in account:
                    if i['invoice'][0]:
                        if not i['invoice'][0] in invoice_ids:
                            inv = self.pool.get('account.invoice').browse(self.cr, self.uid,i['invoice'][0]) 
                            if inv.type == 'out_invoice' and inv.state == 'open':
                                if not i['invoice'][0] in self.invoices:
                                    print '*********************** : ',i['invoice'][0]
                                    self.invoices.append(i['invoice'][0])
                        #end if
                    #end if
                #end for
            #end if
        elif self.flag == False:
            self.invoices = self.ids
        #end if
    #end def
    
    def getInvoices(self):
        print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>',self.invoices;
        return self.pool.get('account.invoice').browse(self.cr, self.uid, self.invoices)
    #end def
    
    def addInvoice(self, invoice):
        if invoice.retail_tax == 'tax':
            self.total_local_sale += invoice.amount_untaxed
            self.total_local_tax += invoice.amount_tax
            
            for tax in invoice.tax_line:
                if self.tax_tax.has_key(tax.name):
                    self.tax_tax[tax.name] += tax.tax_amount
                    self.sale_tax[tax.name] += tax.base_amount
                else:
                    self.tax_tax[tax.name] = tax.tax_amount
                    self.sale_tax[tax.name] = tax.base_amount
            #end for
        elif invoice.retail_tax == 'retail':
            self.total_retail_sale += invoice.amount_untaxed
            self.total_retail_tax += invoice.amount_tax
            self. retail += invoice.amount_total
            for tax in invoice.tax_line:
                if self.retail_tax.has_key(tax.name):
                    self.retail_tax[tax.name] += tax.tax_amount
                    self.sale_retail[tax.name] += tax.base_amount
                else:
                    self.retail_tax[tax.name] = tax.tax_amount
                    self.sale_retail[tax.name] = tax.base_amount
                #end if
            #end for
        #endif
    #end def
    
    def getTaxDetail(self, tax):
        return self.tax_tax[tax];
    
    def getTax(self):
        tax = []
        for i in self.tax_tax:
            tax.append(i)
        return tax
    #end if
    
    def getRetailTaxDetail(self, tax):
        return self.retail_tax[tax];
    
    def getRetailTax(self):
        tax = []
        for i in self.retail_tax:
            tax.append(i)
        return tax
    #end if
    
    def getLocalSale(self, tax):
        return self.sale_tax[tax]
    #end def
    
    def getRetailSale(self, tax):
        return self.sale_retail[tax]
    #end def
    
    def getTotalLocalSale(self):
        return self.total_local_sale
    #end def
    
    def getTotalLocalTax(self):
        return self.total_local_tax
    #end def
    
    def getTotalRetailSale(self):
        return self.total_retail_sale
    #end def
    
    def getTotalRetailTax(self):
        return self.total_retail_tax
    #end def
#end class

report_sxw.report_sxw(
    'report.indianvat.declaration',
    'account.invoice',
    'addons/india/account/report/tax_report.rml',
    parser=account_tax_report,
)