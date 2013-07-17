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
from openerp.report import report_sxw

class pos_details(report_sxw.rml_parse):

    def _get_invoice(self, inv_id):
        res={}
        if inv_id:
            self.cr.execute("select number from account_invoice as ac where id = %s", (inv_id,))
            res = self.cr.fetchone()
            return res[0] or 'Draft'
        else:
            return  ''

    def _get_all_users(self):
        user_obj = self.pool.get('res.users')
        return user_obj.search(self.cr, self.uid, [])

    def _pos_sales_details(self, form):
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        data = []
        result = {}
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('state','in',['done','paid','invoiced']),('company_id','=',company_id)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            for pol in pos.lines:
                result = {
                    'code': pol.product_id.default_code,
                    'name': pol.product_id.name,
                    'invoice_id': pos.invoice_id.id, 
                    'price_unit': pol.price_unit, 
                    'qty': pol.qty, 
                    'discount': pol.discount, 
                    'total': (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)), 
                    'date_order': pos.date_order, 
                    'pos_name': pos.name, 
                    'uom': pol.product_id.uom_id.name
                }
                data.append(result)
                self.total += result['total']
                self.qty += result['qty']
                self.discount += result['discount']
        if data:
            return data
        else:
            return {}

    def _get_qty_total_2(self):
        return self.qty

    def _get_sales_total_2(self):
        return self.total

    def _get_sum_invoice_2(self, form):
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('company_id','=',company_id),('invoice_id','<>',False)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            for pol in pos.lines:
                self.total_invoiced += (pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))
        return self.total_invoiced or False

    def _paid_total_2(self):
        return self.total or 0.0

    def _get_sum_dis_2(self):
        return self.discount or 0.0

    def _get_sum_discount(self, form):
        #code for the sum of discount value
        pos_obj = self.pool.get('pos.order')
        user_obj = self.pool.get('res.users')
        user_ids = form['user_ids'] or self._get_all_users()
        company_id = user_obj.browse(self.cr, self.uid, self.uid).company_id.id
        pos_ids = pos_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('user_id','in',user_ids),('company_id','=',company_id)])
        for pos in pos_obj.browse(self.cr, self.uid, pos_ids):
            for pol in pos.lines:
                self.total_discount += ((pol.price_unit * pol.qty) * (pol.discount / 100))
        return self.total_discount or False

    def _get_payments(self, form):
        statement_line_obj = self.pool.get("account.bank.statement.line")
        pos_order_obj = self.pool.get("pos.order")
        user_ids = form['user_ids'] or self._get_all_users()
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','in',user_ids)])
        data={}
        if pos_ids:
            st_line_ids = statement_line_obj.search(self.cr, self.uid, [('pos_statement_id', 'in', pos_ids)])
            if st_line_ids:
                st_id = statement_line_obj.browse(self.cr, self.uid, st_line_ids)
                a_l=[]
                for r in st_id:
                    a_l.append(r['id'])
                self.cr.execute("select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                                "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id IN %s " \
                                "group by aj.name ",(tuple(a_l),))

                data = self.cr.dictfetchall()
                return data
        else:
            return {}

    def _total_of_the_day(self, objects):
        if self.total:
             if self.total == self.total_invoiced:
                 return self.total
             else:
                 return ((self.total or 0.00) - (self.total_invoiced or 0.00))
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

    def _get_tax_amount(self, form):
        res = {}
        temp = {}
        list_ids = []
        temp2 = 0.0
        user_ids = form['user_ids'] or self._get_all_users()
        pos_order_obj = self.pool.get('pos.order')
        pos_ids = pos_order_obj.search(self.cr, self.uid, [('date_order','>=',form['date_start'] + ' 00:00:00'),('date_order','<=',form['date_end'] + ' 23:59:59'),('state','in',['paid','invoiced','done']),('user_id','in',user_ids)])
        temp.update({'name': ''})
        for order in pos_order_obj.browse(self.cr, self.uid, pos_ids):
            temp2 += order.amount_tax
            for line in order.lines:
                if len(line.product_id.taxes_id):
                    tax = line.product_id.taxes_id[0]
                    res[tax.name] = (line.price_unit * line.qty * (1-(line.discount or 0.0) / 100.0)) + (tax.id in list_ids and res[tax.name] or 0)
                    list_ids.append(tax.id)
                    temp.update({'name': tax.name})
        temp.update({'amount': temp2})
        return [temp] or False

    def _get_user_names(self, user_ids):
        user_obj = self.pool.get('res.users')
        return ', '.join(map(lambda x: x.name, user_obj.browse(self.cr, self.uid, user_ids)))

    def __init__(self, cr, uid, name, context):
        super(pos_details, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.qty = 0.0
        self.total_invoiced = 0.0
        self.discount = 0.0
        self.total_discount = 0.0
        self.localcontext.update({
            'time': time,
            'strip_name': self._strip_name,
            'getpayments': self._get_payments,
            'getsumdisc': self._get_sum_discount,
            'gettotalofthaday': self._total_of_the_day,
            'gettaxamount': self._get_tax_amount,
            'pos_sales_details':self._pos_sales_details,
            'getqtytotal2': self._get_qty_total_2,
            'getsalestotal2': self._get_sales_total_2,
            'getsuminvoice2':self._get_sum_invoice_2,
            'getpaidtotal2': self._paid_total_2,
            'getinvoice':self._get_invoice,
            'get_user_names': self._get_user_names,
        })

report_sxw.report_sxw('report.pos.details', 'pos.order', 'addons/point_of_sale_singer/report/pos_details.rml', parser=pos_details, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
