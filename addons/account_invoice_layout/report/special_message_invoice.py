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
import pooler

class account_invoice_with_message(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_invoice_with_message, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'spcl_msg': self.spcl_msg,
            'invoice_lines': self.invoice_lines,

        })
        self.context = context

    def spcl_msg(self, form):
        account_msg_data = pooler.get_pool(self.cr.dbname).get('notify.message').browse(self.cr, self.uid, form['message'])
        msg = account_msg_data.msg
        return msg


    def invoice_lines(self,invoice):
        result =[]
        sub_total={}
        info=[]
        invoice_list=[]
        res={}
        list_in_seq={}
        ids = self.pool.get('account.invoice.line').search(self.cr, self.uid, [('invoice_id', '=', invoice.id)])
        ids.sort()
        for id in range(0,len(ids)):
            info = self.pool.get('account.invoice.line').browse(self.cr, self.uid,ids[id], self.context.copy())
            list_in_seq[info]=info.sequence
        i=1
        j=0
        final=sorted(list_in_seq.items(), lambda x, y: cmp(x[1], y[1]))
        invoice_list=[x[0] for x in final]
        sum_flag={}
        sum_flag[j]=-1
        for entry in invoice_list:
            res={}

            if entry.state=='article':
                self.cr.execute('select tax_id from account_invoice_line_tax where invoice_line_id=%s', (entry.id,))
                tax_ids=self.cr.fetchall()

                if tax_ids==[]:
                    res['tax_types']=''
                else:
                    tax_names_dict={}
                    for item in range(0,len(tax_ids))    :
                        self.cr.execute('select name from account_tax where id=%s', (tax_ids[item][0],))
                        type=self.cr.fetchone()
                        tax_names_dict[item] =type[0]
                    tax_names = ','.join([tax_names_dict[x] for x in range(0,len(tax_names_dict))])
                    res['tax_types']=tax_names
                res['name']=entry.name
                res['quantity']="%.2f"%(entry.quantity)
                res['price_unit']="%.2f"%(entry.price_unit)
                res['discount']="%.2f"%(entry.discount)
                res['price_subtotal']="%.2f"%(entry.price_subtotal)
                sub_total[i]=entry.price_subtotal
                i=i+1
                res['note']=entry.note
                res['currency']=invoice.currency_id.code
                res['type']=entry.state

                if entry.uos_id.id==False:
                    res['uos']=''
                else:
                    uos_name = self.pool.get('product.uom').read(self.cr,self.uid,entry.uos_id.id,['name'],self.context.copy())
                    res['uos']=uos_name['name']
            else:

                res['quantity']=''
                res['price_unit']=''
                res['discount']=''
                res['tax_types']=''
                res['type']=entry.state
                res['note']=entry.note
                res['uos']=''

                if entry.state=='subtotal':
                    res['name']=entry.name
                    sum=0
                    sum_id=0
                    if sum_flag[j]==-1:
                        temp=1
                    else:
                        temp=sum_flag[j]

                    for sum_id in range(temp,len(sub_total)+1):
                        sum+=sub_total[sum_id]
                    sum_flag[j+1]= sum_id +1

                    j=j+1
                    res['price_subtotal']="%.2f"%(sum)
                    res['currency']=invoice.currency_id.code
                    res['quantity']=''
                    res['price_unit']=''
                    res['discount']=''
                    res['tax_types']=''
                    res['uos']=''
                elif entry.state=='title':
                    res['name']=entry.name
                    res['price_subtotal']=''
                    res['currency']=''
                elif entry.state=='text':
                    res['name']=entry.name
                    res['price_subtotal']=''
                    res['currency']=''
                elif entry.state=='line':
                    res['quantity']='___________________'
                    res['price_unit']='______________________'
                    res['discount']='____________________________________'
                    res['tax_types']='_____________________'
                    res['uos']='_____'
                    res['name']='______________________________________'
                    res['price_subtotal']='___________'
                    res['currency']='_'
                elif entry.state=='break':
                    res['type']=entry.state
                    res['name']=entry.name
                    res['price_subtotal']=''
                    res['currency']=''
                else:
                    res['name']=entry.name
                    res['price_subtotal']=''
                    res['currency']=invoice.currency_id.code

            result.append(res)
        return result

report_sxw.report_sxw('report.notify_account.invoice', 'account.invoice', 'addons/account_invoice_layout/report/special_message_invoice.rml', parser=account_invoice_with_message)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

