import time
from report import report_sxw
import pooler

class l10n_chart_it_servabit_report_libroIVA_debito(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(l10n_chart_it_servabit_report_libroIVA_debito,self).__init__(cr,uid,name,context)
        self.localcontext.update({
            'time': time,
            'get_company': self.get_company,
            'get_periods': self.get_periods,
            'get_lines': self.get_lines,
        })

    def get_company(self,fiscal_year):
        #print 'COMP = ',fiscal_year
        return ""

    def get_periods(self,fiscal_year):
        #print 'Fiscal year id:',fiscal_year.id
        obj=pooler.get_pool(self.cr.dbname).get('account.fiscalyear')
        fy=obj.browse(self.cr,self.uid,fiscal_year.id)
        #print 'Periods = ',fy.period_ids
        res=[rec for rec in fy.period_ids]
        #return fy.periods  => non funziona?!? bool object !?!?
        return res

    def get_invoices(self,period):
        #print 'PERIOD = ',period.name
        obj=pooler.get_pool(self.cr.dbname).get('account.invoice')
        # Selezione tutte le fatture emesse nel periodo
        self.cr.execute("""
                        SELECT id FROM account_invoice
                        WHERE (state='open' OR state='paid') AND
                                period_id="""+str(period.id)+"""
                                AND (type='in_invoice' OR type='in_refund')
                        """)
        ids=self.cr.fetchall()
        #print 'IDS = ',
        if ids:
            ids=[id[0] for id in ids ]
        invoices=obj.browse(self.cr,self.uid,ids)
        #print 'INVOICES = ',invoices
        return invoices

    def get_lines(self,fiscal_year):
        res=[]
        obj_fy=pooler.get_pool(self.cr.dbname).get('account.fiscalyear')
        fy=obj_fy.browse(self.cr,self.uid,fiscal_year.id)
        for period in fy.period_ids:
            invoices=self.get_invoices(period)
            for invoice in invoices:
                d={'periodo': period.name}
                d['protocollo']=invoice.number
            #print 'PARTNER ',invoice.partner_id.name
            causale=invoice.partner_id.name
            #print 'CAUSALE = ',causale
            d['causale']=causale
            d['numero']=invoice.reference
            d['data_doc']=invoice.date_invoice
            for tax in invoice.tax_line:
                #print '\tTAX: ',tax
                d['aliquota']=tax.tax_code_id.name
                d['imponibile']=tax.base
                d['imposta']=tax.amount
                res.append(d)
                d={'periodo':'', 'protocollo':'', 'causale':'', 'numero':'', 'data_doc':'', }
        return res

report_sxw.report_sxw('report.l10n_it.report.libroIVA_debito','account.report_libroiva', 'l10n_it/report/libroIVA_debito.rml', parser=l10n_chart_it_servabit_report_libroIVA_debito,header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
