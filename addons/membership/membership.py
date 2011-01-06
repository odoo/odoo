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

from osv import fields, osv
from tools import config
import time

STATE = [
    ('none', 'Non Member'),
    ('canceled', 'Canceled Member'),
    ('old', 'Old Member'),
    ('waiting', 'Waiting Member'),
    ('invoiced', 'Invoiced Member'),
    ('free', 'Free Member'),
    ('paid', 'Paid Member'),
]

STATE_PRIOR = {
        'none' : 0,
        'canceled' : 1,
        'old' : 2,
        'waiting' : 3,
        'invoiced' : 4,
        'free' : 6,
        'paid' : 7
        }

#~ REQUETE = '''SELECT partner, state FROM (
#~ SELECT members.partner AS partner,
#~ CASE WHEN MAX(members.state) = 0 THEN 'none'
#~ ELSE CASE WHEN MAX(members.state) = 1 THEN 'canceled'
#~ ELSE CASE WHEN MAX(members.state) = 2 THEN 'old'
#~ ELSE CASE WHEN MAX(members.state) = 3 THEN 'waiting'
#~ ELSE CASE WHEN MAX(members.state) = 4 THEN 'invoiced'
#~ ELSE CASE WHEN MAX(members.state) = 6 THEN 'free'
#~ ELSE CASE WHEN MAX(members.state) = 7 THEN 'paid'
#~ END END END END END END END END
    #~ AS state FROM (
#~ SELECT partner,
    #~ CASE WHEN MAX(inv_digit.state) = 4 THEN 7
    #~ ELSE CASE WHEN MAX(inv_digit.state) = 3 THEN 4
    #~ ELSE CASE WHEN MAX(inv_digit.state) = 2 THEN 3
    #~ ELSE CASE WHEN MAX(inv_digit.state) = 1 THEN 1
#~ END END END END
#~ AS state
#~ FROM (
    #~ SELECT p.id as partner,
    #~ CASE WHEN ai.state = 'paid' THEN 4
    #~ ELSE CASE WHEN ai.state = 'open' THEN 3
    #~ ELSE CASE WHEN ai.state = 'proforma' THEN 2
    #~ ELSE CASE WHEN ai.state = 'draft' THEN 2
    #~ ELSE CASE WHEN ai.state = 'cancel' THEN 1
#~ END END END END END
#~ AS state
#~ FROM res_partner p
#~ JOIN account_invoice ai ON (
    #~ p.id = ai.partner_id
#~ )
#~ JOIN account_invoice_line ail ON (
    #~ ail.invoice_id = ai.id
#~ )
#~ JOIN membership_membership_line ml ON (
    #~ ml.account_invoice_line  = ail.id
#~ )
#~ WHERE ml.date_from <= '%s'
#~ AND ml.date_to >= '%s'
#~ GROUP BY
#~ p.id,
#~ ai.state
    #~ )
    #~ AS inv_digit
    #~ GROUP by partner
#~ UNION
#~ SELECT p.id AS partner,
    #~ CASE WHEN  p.free_member THEN 6
    #~ ELSE CASE WHEN p.associate_member IN (
        #~ SELECT ai.partner_id FROM account_invoice ai JOIN
        #~ account_invoice_line ail ON (ail.invoice_id = ai.id AND ai.state = 'paid')
        #~ JOIN membership_membership_line ml ON (ml.account_invoice_line = ail.id)
        #~ WHERE ml.date_from <= '%s'
        #~ AND ml.date_to >= '%s'
    #~ )
    #~ THEN 5
#~ END END
#~ AS state
#~ FROM res_partner p
#~ WHERE p.free_member
#~ OR p.associate_member > 0
#~ UNION
#~ SELECT p.id as partner,
    #~ MAX(CASE WHEN ai.state = 'paid' THEN 2
    #~ ELSE 0
    #~ END)
#~ AS state
#~ FROM res_partner p
#~ JOIN account_invoice ai ON (
    #~ p.id = ai.partner_id
#~ )
#~ JOIN account_invoice_line ail ON (
    #~ ail.invoice_id = ai.id
#~ )
#~ JOIN membership_membership_line ml ON (
    #~ ml.account_invoice_line  = ail.id
#~ )
#~ WHERE ml.date_from < '%s'
#~ AND ml.date_to < '%s'
#~ AND ml.date_from <= ml.date_to
#~ GROUP BY
#~ p.id
#~ )
#~ AS members
#~ GROUP BY members.partner
#~ )
#~ AS final
#~ %s
#~ '''

class membership_line(osv.osv):
    '''Member line'''

    def _check_membership_date(self, cr, uid, ids, context=None):
        '''Check if membership product is not in the past'''

        cr.execute('''
         SELECT MIN(ml.date_to - ai.date_invoice)
         FROM membership_membership_line ml
         JOIN account_invoice_line ail ON (
            ml.account_invoice_line = ail.id
            )
        JOIN account_invoice ai ON (
            ai.id = ail.invoice_id)
        WHERE ml.id in %s
        ''', (tuple(ids),))

        res = cr.fetchall()
        for r in res:
            if r[0] and r[0] < 0:
                return False
        return True

    def _state(self, cr, uid, ids, name, args, context=None):
        '''Compute the state lines'''
        res = {}
        for line in self.browse(cr, uid, ids):
            cr.execute('''
            SELECT i.state, i.id FROM
            account_invoice i 
            WHERE
            i.id = (
                SELECT l.invoice_id FROM
                account_invoice_line l WHERE
                l.id = (
                    SELECT  ml.account_invoice_line FROM
                    membership_membership_line ml WHERE
                    ml.id = %s
                    )
                )
            ''', (line.id,))
            fetched = cr.fetchone()
            if not fetched :
                res[line.id] = 'canceled'
                continue
            istate = fetched[0]
            state = 'none'
            if (istate == 'draft') | (istate == 'proforma'):
                state = 'waiting'
            elif istate == 'open':
                state = 'invoiced'
            elif istate == 'paid':
                state = 'paid'
                inv = self.pool.get('account.invoice').browse(cr, uid, fetched[1])
                for payment in inv.payment_ids:
                    if payment.invoice and payment.invoice.type == 'out_refund':
                        state = 'canceled'
            elif istate == 'cancel':
                state = 'canceled'
            res[line.id] = state
        return res


    _description = __doc__
    _name = 'membership.membership_line'
    _columns = {
            'partner': fields.many2one('res.partner', 'Partner', ondelete='cascade', select=1),
            'date_from': fields.date('From'),
            'date_to': fields.date('To'),
            'date_cancel' : fields.date('Cancel date'),
            'account_invoice_line': fields.many2one('account.invoice.line', 'Account Invoice line'),
            'state': fields.function(_state, method=True, string='State', type='selection', selection=STATE),
            }
    _rec_name = 'partner'
    _order = 'id desc'
    _constraints = [
            (_check_membership_date, 'Error, this membership product is out of date', [])
    ]

membership_line()


class Partner(osv.osv):
    '''Partner'''
    _inherit = 'res.partner'

    def _get_partner_id(self, cr, uid, ids, context=None):
        data_inv = self.pool.get('membership.membership_line').browse(cr, uid, ids, context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner.id)
        ids2 = list_partner
        while ids2:
            ids2 = self.pool.get('res.partner').search(cr, uid, [('associate_member','in',ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _get_invoice_partner(self, cr, uid, ids, context=None):
        data_inv = self.pool.get('account.invoice').browse(cr, uid, ids, context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner_id.id)
        ids2 = list_partner
        while ids2:
            ids2 = self.pool.get('res.partner').search(cr, uid, [('associate_member','in',ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _membership_state(self, cr, uid, ids, name, args, context=None):
        res = {}
        for id in ids:
            res[id] = 'none'
        today = time.strftime('%Y-%m-%d')
        for id in ids:
            partner_data = self.browse(cr,uid,id)
            if partner_data.membership_cancel and today > partner_data.membership_cancel:
                res[id] = 'canceled'
                continue
            if partner_data.membership_stop and today > partner_data.membership_stop:
                res[id] = 'old'
                continue
            s = 4
            if partner_data.member_lines:
                for mline in partner_data.member_lines:
                    if mline.date_to >= today:
                        if mline.account_invoice_line and mline.account_invoice_line.invoice_id:
                            mstate = mline.account_invoice_line.invoice_id.state
                            if mstate == 'paid':
                                s = 0
                                inv = mline.account_invoice_line.invoice_id
                                for payment in inv.payment_ids:
                                    if payment.invoice.type == 'out_refund':
                                        s = 2
                                break
                            elif mstate == 'open' and s!=0:
                                s = 1
                            elif mstate == 'cancel' and s!=0 and s!=1:
                                s = 2
                            elif  (mstate == 'draft' or mstate == 'proforma') and s!=0 and s!=1:
                                s = 3
                if s==4:
                    for mline in partner_data.member_lines:
                        if mline.date_from < today and mline.date_to < today and mline.date_from<=mline.date_to and (mline.account_invoice_line and mline.account_invoice_line.invoice_id.state) == 'paid':
                            s = 5
                        else:
                            s = 6
                if s==0:
                    res[id] = 'paid'
                elif s==1:
                    res[id] = 'invoiced'
                elif s==2:
                    res[id] = 'canceled'
                elif s==3:
                    res[id] = 'waiting'
                elif s==5:
                    res[id] = 'old'
                elif s==6:
                    res[id] = 'none'
            if partner_data.free_member and s!=0:
                res[id] = 'free'
            if partner_data.associate_member:
                res_state = self._membership_state(cr, uid, [partner_data.associate_member.id], name, args, context)
                res[id] = res_state[partner_data.associate_member.id]
        return res

    def _membership_start(self, cr, uid, ids, name, args, context=None):
        '''Return the start date of membership'''
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, uid, ids):
            if partner.associate_member:
                partner_id = partner.associate_member.id
            else:
                partner_id = partner.id
            line_id = member_line_obj.search(cr, uid, [('partner', '=', partner_id)],
                    limit=1, order='date_from')
            if line_id:
                res[partner.id] = member_line_obj.read(cr, uid, line_id[0],
                        ['date_from'])['date_from']
            else:
                res[partner.id] = False
        return res

    def _membership_stop(self, cr, uid, ids, name, args, context=None):
        '''Return the stop date of membership'''
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, uid, ids):
            cr.execute('select membership_state from res_partner where id=%s', (partner.id,))
            data_state = cr.fetchall()
            if partner.associate_member:
                partner_id = partner.associate_member.id
            else:
                partner_id = partner.id
            line_id = member_line_obj.search(cr, uid, [('partner', '=', partner_id)],
                    limit=1, order='date_to desc')
            if line_id:
                res[partner.id] = member_line_obj.read(cr, uid, line_id[0],
                        ['date_to'])['date_to']
            else:
                res[partner.id] = False
        return res

    def _membership_cancel(self, cr, uid, ids, name, args, context=None):
        '''Return the cancel date of membership'''
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.membership_state != 'canceled':
                res[partner.id] = False
            else:
                line_id = member_line_obj.search(cr, uid, [('partner', '=', partner.id)],
                        limit=1, order='date_cancel')
                if line_id:
                    res[partner.id] = member_line_obj.read(cr, uid, line_id[0],
                            ['date_cancel'])['date_cancel']
                else:
                    res[partner.id] = False
        return res

    def _get_partners(self, cr, uid, ids, context={}):
        ids2 = ids
        while ids2:
            ids2 = self.search(cr, uid, [('associate_member','in',ids2)], context=context)
            ids+=ids2
        return ids

    def __get_membership_state(self, *args, **kwargs):
        return self._membership_state(*args, **kwargs)

    _columns = {
        'associate_member': fields.many2one('res.partner', 'Associate member'),
        'member_lines': fields.one2many('membership.membership_line', 'partner', 'Membership'),
        'free_member': fields.boolean('Free member'),
        'membership_amount': fields.float(
                    'Membership amount', digits=(16, 2),
                    help='The price negociated by the partner'),
        'membership_state': fields.function(
                    __get_membership_state, method = True,
                    string = 'Current membership state', type = 'selection',
                    selection = STATE ,store = {
                        'account.invoice':(_get_invoice_partner,['state'], 10),
                        'membership.membership_line':(_get_partner_id,['state'], 10),
                        'res.partner':(_get_partners, ['free_member', 'membership_state', 'associate_member'], 10)
                        }
                    ),
        'membership_start': fields.function(
                    _membership_start, method=True,
                    string = 'Start membership date', type = 'date',
                    store = {
                        'account.invoice':(_get_invoice_partner,['state'], 10),
                        'membership.membership_line':(_get_partner_id,['state'], 10),
                        'res.partner':(lambda self,cr,uid,ids,c={}:ids, ['free_member'], 10)
                        }
                    ),
        'membership_stop': fields.function(
                    _membership_stop, method = True,
                    string = 'Stop membership date', type = 'date',
                    store = {
                        'account.invoice':(_get_invoice_partner,['state'], 10),
                        'membership.membership_line':(_get_partner_id,['state'], 10),
                        'res.partner':(lambda self,cr,uid,ids,c={}:ids, ['free_member'], 10)
                        }
                    ),

        'membership_cancel': fields.function(
                    _membership_cancel, method = True,
                    string = 'Cancel membership date', type='date',
                    store = {
                        'account.invoice':(_get_invoice_partner,['state'], 11),
                        'membership.membership_line':(_get_partner_id,['state'], 10),
                        'res.partner':(lambda self,cr,uid,ids,c={}:ids, ['free_member'], 10)
                        }
                    ),
    }
    _defaults = {
        'free_member': lambda *a: False,
        'membership_cancel' : lambda *d : False,
    }

    def _check_recursion(self, cr, uid, ids):
        level = 100
        while len(ids):
            cr.execute('select distinct associate_member from res_partner where id in %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You can not create recursive associated members.', ['associate_member'])
    ]
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}    
        default = default.copy()
        default['member_lines'] = []
        return super(Partner, self).copy(cr, uid, id, default, context)
    
Partner()

class product_template(osv.osv):
    _inherit = 'product.template'
    _columns = {
            'member_price':fields.float('Member Price', digits=(16, int(config['price_accuracy']))),
            }
product_template()

class Product(osv.osv):

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False):
        if ('product' in context) and (context['product']=='membership_product'):
            model_data_ids_form = self.pool.get('ir.model.data').search(cr,user,[('model','=','ir.ui.view'),('name','in',['membership_products_form','membership_products_tree'])])
            resource_id_form = self.pool.get('ir.model.data').read(cr,user,model_data_ids_form,fields=['res_id','name'])
            dict_model={}
            for i in resource_id_form:
                dict_model[i['name']]=i['res_id']
            if view_type=='form':
                view_id = dict_model['membership_products_form']
            else:
                view_id = dict_model['membership_products_tree']
        return super(Product,self).fields_view_get(cr, user, view_id, view_type, context, toolbar)

    '''Product'''
    _inherit = 'product.product'
    _description = 'product.product'

    _columns = {
            'membership': fields.boolean('Membership', help='Specify if this product is a membership product'),
            'membership_date_from': fields.date('Date from'),
            'membership_date_to': fields.date('Date to'),
#           'member_price':fields.float('Member Price'),
            }

    _defaults = {
            'membership': lambda *args: False
            }
Product()


class Invoice(osv.osv):
    '''Invoice'''

    _inherit = 'account.invoice'

    def action_cancel(self, cr, uid, ids, context=None):
        '''Create a 'date_cancel' on the membership_line object'''
        if context is None:
            context = {}
        member_line_obj = self.pool.get('membership.membership_line')
        today = time.strftime('%Y-%m-%d')
        for invoice in self.browse(cr, uid, ids):
            mlines = member_line_obj.search(cr,uid,
                    [('account_invoice_line','in',
                        [ l.id for l in invoice.invoice_line])], context)
            member_line_obj.write(cr,uid,mlines, {'date_cancel':today}, context)
        return super(Invoice, self).action_cancel(cr, uid, ids, context)
Invoice()


class ReportPartnerMemberYear(osv.osv):
    '''Membership by Years'''

    _name = 'report.partner_member.year'
    _description = __doc__
    _auto = False
    _rec_name = 'year'
    _columns = {
        'year': fields.char('Year', size=4, readonly=True, select=1),
        'canceled_number': fields.integer('Canceled', readonly=True),
        'waiting_number': fields.integer('Waiting', readonly=True),
        'invoiced_number': fields.integer('Invoiced', readonly=True),
        'paid_number': fields.integer('Paid', readonly=True),
        'canceled_amount': fields.float('Canceled', digits=(16, 2), readonly=True),
        'waiting_amount': fields.float('Waiting', digits=(16, 2), readonly=True),
        'invoiced_amount': fields.float('Invoiced', digits=(16, 2), readonly=True),
        'paid_amount': fields.float('Paid', digits=(16, 2), readonly=True),
        'currency': fields.many2one('res.currency', 'Currency', readonly=True,
            select=2),
    }

    def init(self, cr):
        '''Create the view'''
        cr.execute("""
    CREATE OR REPLACE VIEW report_partner_member_year AS (
        SELECT
        MIN(id) AS id,
        COUNT(ncanceled) as canceled_number,
        COUNT(npaid) as paid_number,
        COUNT(ninvoiced) as invoiced_number,
        COUNT(nwaiting) as waiting_number,
        SUM(acanceled) as canceled_amount,
        SUM(apaid) as paid_amount,
        SUM(ainvoiced) as invoiced_amount,
        SUM(awaiting) as waiting_amount,
        year,
        currency
        FROM (SELECT
            CASE WHEN ai.state = 'cancel' THEN ml.id END AS ncanceled,
            CASE WHEN ai.state = 'paid' THEN ml.id END AS npaid,
            CASE WHEN ai.state = 'open' THEN ml.id END AS ninvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN ml.id END AS nwaiting,
            CASE WHEN ai.state = 'cancel'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS acanceled,
            CASE WHEN ai.state = 'paid'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS apaid,
            CASE WHEN ai.state = 'open'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS ainvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS awaiting,
            TO_CHAR(ml.date_from, 'YYYY') AS year,
            ai.currency_id AS currency,
            MIN(ml.id) AS id
            FROM membership_membership_line ml
            JOIN (account_invoice_line ail
                LEFT JOIN account_invoice ai
                ON (ail.invoice_id = ai.id))
            ON (ml.account_invoice_line = ail.id)
            JOIN res_partner p
            ON (ml.partner = p.id)
            GROUP BY TO_CHAR(ml.date_from, 'YYYY'), ai.state,
            ai.currency_id, ml.id) AS foo
        GROUP BY year, currency)
                """)

ReportPartnerMemberYear()


class ReportPartnerMemberYearNew(osv.osv):
    '''New Membership by Years'''

    _name = 'report.partner_member.year_new'
    _description = __doc__
    _auto = False
    _rec_name = 'year'
    _columns = {
        'year': fields.char('Year', size=4, readonly=True, select=1),
        'canceled_number': fields.integer('Canceled', readonly=True),
        'waiting_number': fields.integer('Waiting', readonly=True),
        'invoiced_number': fields.integer('Invoiced', readonly=True),
        'paid_number': fields.integer('Paid', readonly=True),
        'canceled_amount': fields.float('Canceled', digits=(16, 2), readonly=True),
        'waiting_amount': fields.float('Waiting', digits=(16, 2), readonly=True),
        'invoiced_amount': fields.float('Invoiced', digits=(16, 2), readonly=True),
        'paid_amount': fields.float('Paid', digits=(16, 2), readonly=True),
        'currency': fields.many2one('res.currency', 'Currency', readonly=True,
            select=2),
    }

    def init(self, cursor):
        '''Create the view'''
        cursor.execute("""
        CREATE OR REPLACE VIEW report_partner_member_year_new AS (
        SELECT
        MIN(id) AS id,
        COUNT(ncanceled) AS canceled_number,
        COUNT(npaid) AS paid_number,
        COUNT(ninvoiced) AS invoiced_number,
        COUNT(nwaiting) AS waiting_number,
        SUM(acanceled) AS canceled_amount,
        SUM(apaid) AS paid_amount,
        SUM(ainvoiced) AS invoiced_amount,
        SUM(awaiting) AS waiting_amount,
        year,
        currency
        FROM (SELECT
            CASE WHEN ai.state = 'cancel' THEN ml2.id END AS ncanceled,
            CASE WHEN ai.state = 'paid' THEN ml2.id END AS npaid,
            CASE WHEN ai.state = 'open' THEN ml2.id END AS ninvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN ml2.id END AS nwaiting,
            CASE WHEN ai.state = 'cancel'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS acanceled,
            CASE WHEN ai.state = 'paid'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS apaid,
            CASE WHEN ai.state = 'open'
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS ainvoiced,
            CASE WHEN (ai.state = 'draft' OR ai.state = 'proforma')
                THEN SUM(ail.price_unit * ail.quantity * (1 - ail.discount / 100))
            ELSE 0 END AS awaiting,
            TO_CHAR(ml2.date_from, 'YYYY') AS year,
            ai.currency_id AS currency,
            MIN(ml2.id) AS id
            FROM (SELECT
                    partner AS id,
                    MIN(date_from) AS date_from
                    FROM membership_membership_line
                    GROUP BY partner
                ) AS ml1
                JOIN membership_membership_line ml2
                JOIN (account_invoice_line ail
                    LEFT JOIN account_invoice ai
                    ON (ail.invoice_id = ai.id))
                ON (ml2.account_invoice_line = ail.id)
                ON (ml1.id = ml2.partner AND ml1.date_from = ml2.date_from)
            JOIN res_partner p
            ON (ml2.partner = p.id)
            GROUP BY TO_CHAR(ml2.date_from, 'YYYY'), ai.state,
            ai.currency_id, ml2.id) AS foo
        GROUP BY year, currency
        )
    """)

ReportPartnerMemberYearNew()

class account_invoice_line(osv.osv):
    _inherit='account.invoice.line'
    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context={}
        res = super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)
        member_line_obj = self.pool.get('membership.membership_line')
        for line in self.browse(cr, uid, ids):
            if line.invoice_id.type == 'out_invoice':
                ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line','=',line.id)])
                if line.product_id and line.product_id.membership and not ml_ids:
                    # Product line has changed to a membership product
                    date_from = line.product_id.membership_date_from
                    date_to = line.product_id.membership_date_to
                    if line.invoice_id.date_invoice > date_from and line.invoice_id.date_invoice < date_to:
                        date_from = line.invoice_id.date_invoice
                    line_id = member_line_obj.create(cr, uid, {
                        'partner': line.invoice_id.partner_id.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'account_invoice_line': line.id,
                        })
                if line.product_id and not line.product_id.membership and ml_ids:
                    # Product line has changed to a non membership product
                    member_line_obj.unlink(cr, uid, ml_ids, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if not context:
            context={}
        member_line_obj = self.pool.get('membership.membership_line')
        for id in ids:
            ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line','=',id)])
            member_line_obj.unlink(cr, uid, ml_ids, context=context)
        return super(account_invoice_line, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context={}):
        result = super(account_invoice_line, self).create(cr, uid, vals, context)
        line = self.browse(cr, uid, result)
        if line.invoice_id.type == 'out_invoice':
            member_line_obj = self.pool.get('membership.membership_line')
            ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line','=',line.id)])
            if line.product_id and line.product_id.membership and not ml_ids:
                # Product line is a membership product
                date_from = line.product_id.membership_date_from
                date_to = line.product_id.membership_date_to
                if line.invoice_id.date_invoice > date_from and line.invoice_id.date_invoice < date_to:
                    date_from = line.invoice_id.date_invoice
                line_id = member_line_obj.create(cr, uid, {
                    'partner': line.invoice_id.partner_id and line.invoice_id.partner_id.id or False,
                    'date_from': date_from,
                    'date_to': date_to,
                    'account_invoice_line': line.id,
                    })
        return result

account_invoice_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
