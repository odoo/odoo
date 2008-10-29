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
from report import report_sxw
import pooler

class account_invoice_intrastat(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_invoice_intrastat, self).__init__(cr, uid, name, context)
        self.total=0
        self.localcontext.update({
            'time': time,
            'get_tax_code':self._get_tax_code,
            'get_tax_note':self._get_tax_note,
            'get_origin':self._get_origin,
            'get_line_by_origin':self._get_line_by_origin,
            #'gross_weight' : self._gross_weight,
            'total_weight' : self._total_weight,
            'get_incoterm':self._get_incoterm,
            'get_ref':self._get_ref,
            'get_product_code': self._get_product_code,
            'get_product_name': self._get_product_name,
        })

    def _get_origin(self,invoice_id):
        self.cr.execute("select distinct origin from account_invoice_line where invoice_id=%d" % (invoice_id))
        res = self.cr.fetchall() or []
        res=map(lambda x:x[0],res)
        if not len(res):
            res.append('-1')
        return res


    def _get_line_by_origin(self,origin,invoice_id,lang='en_US'):
        line_obj=self.pool.get('account.invoice.line')
        if not origin and origin!='-1':
            invoice_line_ids=line_obj.search(self.cr,self.uid,[('invoice_id','=',invoice_id),('origin','=',False)])
        else:
            invoice_line_ids = line_obj.search(self.cr,self.uid,[('invoice_id','=',invoice_id),('origin','=',origin)])
        res= line_obj.browse(self.cr,self.uid,invoice_line_ids,context={'lang':lang})
        return res

    def _get_ref(self,invoice):
        if invoice.type in ('out_invoice','out_refund'):
            if invoice.reference_type in ('customer_ref'):
                return invoice.reference
            sale_obj=pooler.get_pool(self.cr.dbname).get('sale.order')
            sale_ids=sale_obj.search(self.cr,self.uid,[('invoice_ids','=',[invoice.id])])
            sales=sale_obj.browse(self.cr,self.uid,sale_ids)
            if len(sales):
                return sales[0].client_order_ref
        elif invoice.type in ('in_invoice','in_refund'):
            purchase_obj=pooler.get_pool(self.cr.dbname).get('purchase.order')
            purchase_ids=purchase_obj.search(self.cr,self.uid,[('invoice_id','=',invoice.id)])
            purchases=purchase_obj.browse(self.cr,self.uid,purchase_ids)
            if len(purchases):
                return purchases[0].ref
        return False

    def _get_tax_code(self, tax_name):
        tax_obj=pooler.get_pool(self.cr.dbname).get('account.tax')
        ids = tax_obj.search(self.cr, self.uid, [('name','ilike',tax_name)])
        if len(ids) > 0:
            tax = tax_obj.browse(self.cr,self.uid,ids)[0]
            tax_name=tax.label
        return tax_name
    def _get_tax_note(self, tax_name,lang):
        tax_obj=pooler.get_pool(self.cr.dbname).get('account.tax')
        ids = tax_obj.search(self.cr, self.uid, [('name','ilike',tax_name)])
        if len(ids) > 0:
            tax = tax_obj.browse(self.cr,self.uid,ids,context={'lang':lang})[0]
            tax_note=tax.note
        return tax_note

    def _total_weight(self, o):
        res = []
        self.cr.execute("""
            select
                intrastat_code.name,
                sum(
                    case when uom.category_id != puom.category_id then pt.weight_net * inv_line.quantity
                        else
                            case when uom.factor_inv_data > 0
                                then
                                    pt.weight_net * inv_line.quantity * uom.factor_inv_data
                                else
                                    pt.weight_net * inv_line.quantity / uom.factor
                            end
                        end
                    ) as weight
            from
                report_intrastat_code intrastat_code
                left join (product_template pt
                    left join (product_product pp
                        left join (account_invoice_line inv_line
                            left join account_invoice inv on (inv.id=inv_line.invoice_id))
                        on (inv_line.product_id=pp.id))
                    on (pt.id=pp.product_tmpl_id))
                on (pt.intrastat_id=intrastat_code.id)
                left join product_uom uom on uom.id=inv_line.uos_id
                left join product_uom puom on puom.id = pt.uom_id
            where
                inv.id=%d
            group by
                intrastat_code.name
            order by
                intrastat_code.name
        """%(o.id))
        #self.cr.execute('select r.name, sum(t.weight_net * l.quantity) from report_intrastat_code r, product_template t, product_product p, account_invoice_line l, account_invoice a where r.id = t.intrastat_id and t.id = p.product_tmpl_id and p.id = l.product_id and  l.invoice_id = a.id and a.id =%d group by(r.name)' %(o.id))
        res = self.cr.fetchall() or []
        return res
    def _get_incoterm(self, code):
        print code
        incoterm_obj=pooler.get_pool(self.cr.dbname).get('stock.incoterms')
        incoterm_ids = incoterm_obj.search(self.cr,self.uid,[('code','=',code)])
        incoterm=incoterm_obj.browse(self.cr,self.uid,incoterm_ids)[0]
        return incoterm.code

    def _get_product_code(self, product_id, partner_id):
        product_obj=pooler.get_pool(self.cr.dbname).get('product.product')
        product = product_obj.browse(self.cr,self.uid, [product_id])[0]
        for supinfo in product.seller_ids:
            if supinfo.name.id == partner_id:
                return ( supinfo.product_code and  ("[" + supinfo.product_code + "] ") or '')  + supinfo.product_name
        return False

    def _get_product_name(self, product_id):
        product_obj=pooler.get_pool(self.cr.dbname).get('product.product')
        prod_names = product_obj.name_get(self.cr,self.uid,[product_id])
        return prod_names[0][1]


report_sxw.report_sxw('report.account.invoice.intrastat', 'account.invoice', 'addons/report_intrastat/report/invoice.rml', parser=account_invoice_intrastat)

