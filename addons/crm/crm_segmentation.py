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

from openerp.osv import fields,osv,orm

class crm_segmentation(osv.osv):
    '''
        A segmentation is a tool to automatically assign categories on partners.
        These assignations are based on criterions.
    '''
    _name = "crm.segmentation"
    _description = "Partner Segmentation"

    _columns = {
        'name': fields.char('Name', required=True, help='The name of the segmentation.'),
        'description': fields.text('Description'),
        'categ_id': fields.many2one('res.partner.category', 'Partner Category',\
                         required=True, help='The partner category that will be \
added to partners that match the segmentation criterions after computation.'),
        'exclusif': fields.boolean('Exclusive', help='Check if the category is limited to partners that match the segmentation criterions.\
                        \nIf checked, remove the category from partners that doesn\'t match segmentation criterions'),
        'state': fields.selection([('not running','Not Running'),\
                    ('running','Running')], 'Execution Status', readonly=True),
        'partner_id': fields.integer('Max Partner ID processed'),
        'segmentation_line': fields.one2many('crm.segmentation.line', \
                            'segmentation_id', 'Criteria', required=True),
        'sales_purchase_active': fields.boolean('Use The Sales Purchase Rules', help='Check if you want to use this tab as part of the segmentation rule. If not checked, the criteria beneath will be ignored')
    }
    _defaults = {
        'partner_id': lambda *a: 0,
        'state': lambda *a: 'not running',
    }

    def process_continue(self, cr, uid, ids, start=False):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Process continue’s IDs"""

        partner_obj = self.pool.get('res.partner')
        categs = self.read(cr, uid, ids, ['categ_id', 'exclusif', 'partner_id',\
                                 'sales_purchase_active', 'profiling_active'])
        for categ in categs:
            if start:
                if categ['exclusif']:
                    cr.execute('delete from res_partner_res_partner_category_rel \
                            where category_id=%s', (categ['categ_id'][0],))

            id = categ['id']

            cr.execute('select id from res_partner order by id ')
            partners = [x[0] for x in cr.fetchall()]

            if categ['sales_purchase_active']:
                to_remove_list=[]
                cr.execute('select id from crm_segmentation_line where segmentation_id=%s', (id,))
                line_ids = [x[0] for x in cr.fetchall()]

                for pid in partners:
                    if (not self.pool.get('crm.segmentation.line').test(cr, uid, line_ids, pid)):
                        to_remove_list.append(pid)
                for pid in to_remove_list:
                    partners.remove(pid)

            for partner in partner_obj.browse(cr, uid, partners):
                category_ids = [categ_id.id for categ_id in partner.category_id]
                if categ['categ_id'][0] not in category_ids:
                    cr.execute('insert into res_partner_res_partner_category_rel (category_id,partner_id) \
                            values (%s,%s)', (categ['categ_id'][0], partner.id))

            self.write(cr, uid, [id], {'state':'not running', 'partner_id':0})
        return True

    def process_stop(self, cr, uid, ids, *args):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Process stop’s IDs"""

        return self.write(cr, uid, ids, {'state':'not running', 'partner_id':0})

    def process_start(self, cr, uid, ids, *args):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Process start’s IDs """

        self.write(cr, uid, ids, {'state':'running', 'partner_id':0})
        return self.process_continue(cr, uid, ids, start=True)

class crm_segmentation_line(osv.osv):
    """ Segmentation line """
    _name = "crm.segmentation.line"
    _description = "Segmentation line"

    _columns = {
        'name': fields.char('Rule Name', required=True),
        'segmentation_id': fields.many2one('crm.segmentation', 'Segmentation'),
        'expr_name': fields.selection([('sale','Sale Amount'),
                        ('purchase','Purchase Amount')], 'Control Variable', required=True),
        'expr_operator': fields.selection([('<','<'),('=','='),('>','>')], 'Operator', required=True),
        'expr_value': fields.float('Value', required=True),
        'operator': fields.selection([('and','Mandatory Expression'),\
                        ('or','Optional Expression')],'Mandatory / Optional', required=True),
    }
    _defaults = {
        'expr_name': lambda *a: 'sale',
        'expr_operator': lambda *a: '>',
        'operator': lambda *a: 'and'
    }
    def test(self, cr, uid, ids, partner_id):

        """ @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: List of Test’s IDs """

        expression = {'<': lambda x,y: x<y, '=':lambda x,y:x==y, '>':lambda x,y:x>y}
        ok = False
        lst = self.read(cr, uid, ids)
        for l in lst:
            cr.execute('select * from ir_module_module where name=%s and state=%s', ('account','installed'))
            if cr.fetchone():
                if l['expr_name']=='sale':
                    cr.execute('SELECT SUM(l.price_unit * l.quantity) ' \
                            'FROM account_invoice_line l, account_invoice i ' \
                            'WHERE (l.invoice_id = i.id) ' \
                                'AND i.partner_id = %s '\
                                'AND i.type = \'out_invoice\'',
                            (partner_id,))
                    value = cr.fetchone()[0] or 0.0
                    cr.execute('SELECT SUM(l.price_unit * l.quantity) ' \
                            'FROM account_invoice_line l, account_invoice i ' \
                            'WHERE (l.invoice_id = i.id) ' \
                                'AND i.partner_id = %s '\
                                'AND i.type = \'out_refund\'',
                            (partner_id,))
                    value -= cr.fetchone()[0] or 0.0
                elif l['expr_name']=='purchase':
                    cr.execute('SELECT SUM(l.price_unit * l.quantity) ' \
                            'FROM account_invoice_line l, account_invoice i ' \
                            'WHERE (l.invoice_id = i.id) ' \
                                'AND i.partner_id = %s '\
                                'AND i.type = \'in_invoice\'',
                            (partner_id,))
                    value = cr.fetchone()[0] or 0.0
                    cr.execute('SELECT SUM(l.price_unit * l.quantity) ' \
                            'FROM account_invoice_line l, account_invoice i ' \
                            'WHERE (l.invoice_id = i.id) ' \
                                'AND i.partner_id = %s '\
                                'AND i.type = \'in_refund\'',
                            (partner_id,))
                    value -= cr.fetchone()[0] or 0.0
                res = expression[l['expr_operator']](value, l['expr_value'])
                if (not res) and (l['operator']=='and'):
                    return False
                if res:
                    return True
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

