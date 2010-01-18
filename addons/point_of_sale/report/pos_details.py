# -*- encoding: utf-8 -*-
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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw


class pos_details(report_sxw.rml_parse):

    def _get_invoice(self,inv_id,user):
        res={}
        self.cr.execute("select name from account_invoice as ac where id = %d" %(inv_id))
        res = self.cr.fetchone()
        if res:
            return res[0]
        else:
            return  ''

    def _pos_sales_details(self,form,user):
        data={}
        self.cr.execute ("select po.name as pos_name,po.date_order,pt.name ,pol.qty,pol.price_unit,pol.discount,po.invoice_id,sum((pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))) as Total " \
                         "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt,res_users as ru,res_company as rc " \
                         "where  pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id and po.state  in ('done','paid','invoiced') " \
                         "and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  >= %s and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  <= %s " \
                         "and po.user_id = ru.id and rc.id = %s and ru.id = %s " \
                         "group by po.name,pol.qty,po.date_order,pt.name,pol.price_unit,pol.discount,po.invoice_id " \
                             ,(form['date_start'],form['date_end'],str(user.company_id.id),str(self.uid)))
        data=self.cr.dictfetchall()
        if data:
            for d in data:
                self.total += d['total']
                self.qty += d['qty']
                return data
        else:
            return {}

    def _get_qty_total_2(self, form,user):
        qty=[]
        self.cr.execute("select sum(pol.qty) as qty " \
                        "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt,res_users as ru,res_company as rc " \
                        "where  pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id and po.state  in ('done','paid','invoiced') " \
                        " and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  >= %s and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  <= %s " \
                        "and po.user_id = ru.id and rc.id = %s and ru.id = %s " \
                         ,(form['date_start'],form['date_end'],str(user.company_id.id),str(self.uid)))
        qty = self.cr.fetchone()
        return qty[0] or 0.00

    def _get_sales_total_2(self, form,user):
        self.cr.execute("sELECT sum((pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))) as Total from  pos_order_line as pol , pos_order po, product_product as pp,product_template as pt  where po.company_id='%s' and po.id=pol.order_id and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  >= '%s' and  to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  <= '%s' and po.state in ('paid','invoiced','done') and pt.id=pp.product_tmpl_id and pol.product_id=pp.id"% (str(user.company_id.id),form['date_start'],form['date_end']))
        res2=self.cr.fetchone()
        return res2 and res2[0] or 0.0

    def _get_sum_invoice_2(self,form,user):
        res2=[]
        self.cr.execute ("select sum(pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))" \
                         "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt ,res_users as ru,res_company as rc " \
                         "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id and po.state  in('invoiced')  " \
                         "and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  >= %s and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  <= %s " \
                         "and po.user_id = ru.id and rc.id = %s and ru.id = %s " \
                         ,(form['date_start'],form['date_end'],str(user.company_id.id),str(self.uid)))
        res2=self.cr.fetchone()
        self.total_invoiced=res2[0]
        return res2[0] or False

    def _paid_total_2(self,form,user):
        res3=[]
        self.cr.execute ("select sum(pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))" \
                         "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt, res_users as ru,res_company as rc " \
                         "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id and po.state  in('paid','invoiced','done')  " \
                         "and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  >= %s and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date  <= %s " \
                         "and po.user_id = ru.id and rc.id = %s and ru.id = %s " \
                         ,(form['date_start'],form['date_end'],str(user.company_id.id),str(self.uid)))
        res3=self.cr.fetchone()
        self.total_paid=res3[0]
        return res3[0] or False

#    def _get_qty_total(self, objects):
#        #code for the sum of qty_total
#        return reduce(lambda acc, object:
#                                        acc + reduce(
#                                                lambda sum_qty, line:
#                                                        sum_qty + line.qty,
#                                                object.lines,
#                                                0),
#                                    objects,
#                                    0)

    def _get_sum_discount(self, objects):
        #code for the sum of discount value
        return reduce(lambda acc, object:
                                        acc + reduce(
                                                lambda sum_dis, line:
                                                        sum_dis + ((line.price_unit * line.qty) * (line.discount / 100)),
                                                object.lines,
                                                0.0),
                                    objects,
                                    0.0)

    def _get_payments(self, form,user, ignore_gift=False):
#        gift_journal_id = None
#        if ignore_gift:
#            config_journal_ids = self.pool.get("pos.config.journal").search(self.cr, self.uid, [('code', '=', 'GIFT')])
#            if len(config_journal_ids):
#                config_journal = self.pool.get("pos.config.journal").browse(self.cr, self.uid, config_journal_ids, {})[0]
#                gift_journal_id = config_journal.journal_id.id
#
#        result = {}
#        for obj in objects:
#            for payment in obj.statement_ids:
#                result[payment.journal_id] = result.get(payment.journal_id, 0.0) + payment.amount
#        return result
        statement_line_obj = self.pool.get("account.bank.statement.line")
        gift_journal_id = None
        if ignore_gift:
            config_journal_ids = self.pool.get("pos.config.journal").search(self.cr, self.uid, [('code', '=', 'GIFT')])
            if len(config_journal_ids):
                config_journal = self.pool.get("pos.config.journal").browse(self.cr, self.uid, config_journal_ids, {})[0]
                gift_journal_id = config_journal.journal_id.id
        pos_ids=self.pool.get("pos.order").search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','=',self.uid)])
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id :
                    a_l.append(r['id'])
                    a = ','.join(map(str,a_l))
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id in (%s) " \
                                "group by aj.name " \
                                %(a))

                data=self.cr.dictfetchall()
                return data
        else:
            return {}

    def _total_of_the_day(self, objects):
        if self.total_paid:
             if self.total_paid == self.total_invoiced :
                 return self.total_paid
             else:
                 return ((self.total_paid or 0.00) - (self.total_invoiced or 0.00))
        else:
            return False

    def _sum_invoice(self, objects):
        return reduce(lambda acc, obj:
                        acc + obj.invoice_id.amount_total,
                        [o for o in objects if o.invoice_id and o.invoice_id.number],
                        0.0)

    def _ellipsis(self, orig_str, maxlen=100, ellipsis='...'):
        maxlen = maxlen - len(ellipsis)
        if maxlen <= 0:
            maxlen = 1
        new_str = orig_str[:maxlen]
        return new_str

    def _strip_name(self, name, maxlen=50):
        return self._ellipsis(name, maxlen, ' ...')

    def _get_tax_amount(self, form,user):
        res = {}
        temp={}
        list_ids = []
        c=[]
        temp2 = 0.0
        pos_ids=self.pool.get("pos.order").search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','=',self.uid)])
        temp.update({'name':''})
        for order in self.pool.get("pos.order").browse(self.cr, self.uid, pos_ids):
            temp2 +=order.amount_tax
            for line in order.lines:
                if len(line.product_id.taxes_id):
                    tax = line.product_id.taxes_id[0]
                    res[tax.name] = (line.price_unit * line.qty * (1-(line.discount or 0.0) / 100.0)) + (tax.id in list_ids and res[tax.name] or 0)
                    list_ids.append(tax.id)
                    temp.update({'name':tax.name})
        temp.update({'amount':temp2})
        return [temp] or False

#    def _get_period(self, form):
#        min_date = form['date_start']
#        max_date = form['date_end']
#        if min_date == max_date:
#            return '%s' % min_date
#        else:
#            return '%s - %s' % (min_date, max_date)
    def _get_period(self, form):
        return form['date_start']

    def _get_period2(self,form):
        return form['date_end']

    def __init__(self, cr, uid, name, context):
        super(pos_details, self).__init__(cr, uid, name, context)
        self.total = 0.0
        self.qty = 0.0
        self.invoice_id = ''
        self.total_paid = 0.0
        self.total_invoiced = 0.0
        self.localcontext.update({
            'time': time,
            'strip_name': self._strip_name,
            'getpayments': self._get_payments,
            'getsumdisc': self._get_sum_discount,
            'gettotalofthaday': self._total_of_the_day,
            'gettaxamount': self._get_tax_amount,
            'getperiod': self._get_period,
            'getperiod2':self._get_period2,
            'pos_sales_details':self._pos_sales_details,
            'getqtytotal2': self._get_qty_total_2,
            'getsalestotal2': self._get_sales_total_2,
            'getsuminvoice2':self._get_sum_invoice_2,
            'getpaidtotal2': self._paid_total_2,
            'getinvoice':self._get_invoice,
        })

report_sxw.report_sxw('report.pos.details', 'pos.order', 'addons/point_of_sale_singer/report/pos_details.rml', parser=pos_details, header=None)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

