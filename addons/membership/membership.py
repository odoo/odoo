# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import tools
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import UserError

STATE = [
    ('none', 'Non Member'),
    ('canceled', 'Cancelled Member'),
    ('old', 'Old Member'),
    ('waiting', 'Waiting Member'),
    ('invoiced', 'Invoiced Member'),
    ('free', 'Free Member'),
    ('paid', 'Paid Member'),
]


class membership_line(osv.osv):
    _name = 'membership.membership_line'
    _description = __doc__

    def _get_partners(self, cr, uid, ids, context=None):
        list_membership_line = []
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.pool.get('res.partner').browse(cr, uid, ids, context=context):
            if partner.member_lines:
                list_membership_line += member_line_obj.search(cr, uid, [('id', 'in', [ l.id for l in partner.member_lines])], context=context)
        return list_membership_line

    def _get_membership_lines(self, cr, uid, ids, context=None):
        list_membership_line = []
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
            if invoice.invoice_line_ids:
                list_membership_line += member_line_obj.search(cr, uid, [('account_invoice_line', 'in', [ l.id for l in invoice.invoice_line_ids])], context=context)
        return list_membership_line

    def _check_membership_date(self, cr, uid, ids, context=None):
        """Check if membership product is not in the past """

        cr.execute('''
         SELECT MIN(ml.date_to - ai.date_invoice)
             FROM membership_membership_line ml
             JOIN account_invoice_line ail ON (
                ml.account_invoice_line = ail.id
                )
            JOIN account_invoice ai ON (
            ai.id = ail.invoice_id)
            WHERE ml.id IN %s''', (tuple(ids),))
        res = cr.fetchall()
        for r in res:
            if r[0] and r[0] < 0:
                return False
        return True

    def _state(self, cr, uid, ids, name, args, context=None):
        """Compute the state lines """
        res = {}
        inv_obj = self.pool.get('account.invoice')
        for line in self.browse(cr, uid, ids, context=context):
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
            if not fetched:
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
                inv = inv_obj.browse(cr, uid, fetched[1], context=context)
                for payment in inv.payment_ids:
                    if payment.invoice_ids and any(inv.type == 'out_refund' for inv in payment.invoice_ids):
                        state = 'canceled'
            elif istate == 'cancel':
                state = 'canceled'
            res[line.id] = state
        return res

    _columns = {
        'partner': fields.many2one('res.partner', 'Partner', ondelete='cascade', select=1),
        'membership_id': fields.many2one('product.product', string="Membership", required=True),
        'date_from': fields.date('From', readonly=True),
        'date_to': fields.date('To', readonly=True),
        'date_cancel': fields.date('Cancel date'),
        'date': fields.date('Join Date', help="Date on which member has joined the membership"),
        'member_price': fields.float('Membership Fee', digits_compute= dp.get_precision('Product Price'), required=True, help='Amount for the membership'),
        'account_invoice_line': fields.many2one('account.invoice.line', 'Account Invoice line', readonly=True),
        'account_invoice_id': fields.related('account_invoice_line', 'invoice_id', type='many2one', relation='account.invoice', string='Invoice', readonly=True),
        'state': fields.function(_state,
                        string='Membership Status', type='selection',
                        selection=STATE, store = {
                        'account.invoice': (_get_membership_lines, ['state'], 10),
                        'res.partner': (_get_partners, ['membership_state'], 12),
                        }, help="""It indicates the membership status.
                        -Non Member: A member who has not applied for any membership.
                        -Cancelled Member: A member who has cancelled his membership.
                        -Old Member: A member whose membership date has expired.
                        -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
                        -Invoiced Member: A member whose invoice has been created.
                        -Paid Member: A member who has paid the membership amount."""),
        'company_id': fields.related('account_invoice_line', 'invoice_id', 'company_id', type="many2one", relation="res.company", string="Company", readonly=True, store=True)
    }
    _rec_name = 'partner'
    _order = 'id desc'
    _constraints = [
        (_check_membership_date, 'Error, this membership product is out of date', [])
    ]


class Partner(osv.osv):
    _inherit = 'res.partner'

    def _get_partner_id(self, cr, uid, ids, context=None):
        member_line_obj = self.pool.get('membership.membership_line')
        res_obj = self.pool.get('res.partner')
        data_inv = member_line_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner.id)
        ids2 = list_partner
        while ids2:
            ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _get_invoice_partner(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        res_obj = self.pool.get('res.partner')
        data_inv = inv_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner_id.id)
        ids2 = list_partner
        while ids2:
            ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _cron_update_membership(self, cr, uid, context=None):
        partner_ids = self.search(cr, uid, [('membership_state', '=', 'paid')], context=context)
        if partner_ids:
            self._store_set_values(cr, uid, partner_ids, ['membership_state'], context=context)

    def _membership_state(self, cr, uid, ids, name, args, context=None):
        """This Function return Membership State For Given Partner. """
        res = {}
        for id in ids:
            res[id] = 'none'
        today = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            partner_data = self.browse(cr, uid, id, context=context)
            if partner_data.membership_cancel and today > partner_data.membership_cancel:
                res[id] = 'free' if partner_data.free_member else 'canceled'
                continue
            if partner_data.membership_stop and today > partner_data.membership_stop:
                res[id] = 'free' if partner_data.free_member else 'old'
                continue

            s = 4
            if partner_data.member_lines:
                for mline in partner_data.member_lines:
                    if mline.date_to >= today and mline.date_from <= today:
                        if mline.account_invoice_line and mline.account_invoice_line.invoice_id:
                            mstate = mline.account_invoice_line.invoice_id.state
                            if mstate == 'paid':
                                s = 0
                                inv = mline.account_invoice_line.invoice_id
                                for payment in inv.payment_ids:
                                    if payment.invoice_ids and any(inv.type == 'out_refund' for inv in payment.invoice_ids):
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
                        if mline.date_from < today and mline.date_to < today and mline.date_from <= mline.date_to and mline.account_invoice_line and mline.account_invoice_line.invoice_id.state == 'paid':
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
                res_state = self._membership_state(cr, uid, [partner_data.associate_member.id], name, args, context=context)
                res[id] = res_state[partner_data.associate_member.id]
        return res

    def _membership_date(self, cr, uid, ids, name, args, context=None):
        """Return  date of membership"""
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.associate_member:
                partner_id = partner.associate_member.id
            else:
                partner_id = partner.id
            res[partner.id] = dict()

            if 'membership_start' in name:
                res[partner.id]['membership_start'] = False
                line_id = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('date_cancel','=',False)],
                            limit=1, order='date_from', context=context)
                if line_id:
                    res[partner.id]['membership_start'] = member_line_obj.read(cr, uid, [line_id[0]],
                            ['date_from'], context=context)[0]['date_from']
            if 'membership_stop' in name:
                res[partner.id]['membership_stop'] = False
                line_id1 = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('date_cancel','=',False)],
                            limit=1, order='date_to desc', context=context)
                if line_id1:
                    res[partner.id]['membership_stop'] = member_line_obj.read(cr, uid, [line_id1[0]],
                                ['date_to'], context=context)[0]['date_to']
            if 'membership_cancel' in name:
                res[partner.id]['membership_cancel'] = False
                if partner.membership_state == 'canceled':
                    line_id2 = member_line_obj.search(cr, uid, [('partner', '=', partner.id)], limit=1, order='date_cancel', context=context)
                    if line_id2:
                        res[partner.id]['membership_cancel'] = member_line_obj.read(cr, uid, [line_id2[0]], ['date_cancel'], context=context)[0]['date_cancel']
        return res

    def _get_partners(self, cr, uid, ids, context=None):
        ids2 = ids
        while ids2:
            ids2 = self.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            ids += ids2
        return ids

    def __get_membership_state(self, *args, **kwargs):
        return self._membership_state(*args, **kwargs)

    _columns = {
        'associate_member': fields.many2one('res.partner', 'Associate Member',help="A member with whom you want to associate your membership.It will consider the membership state of the associated member."),
        'member_lines': fields.one2many('membership.membership_line', 'partner', 'Membership'),
        'free_member': fields.boolean('Free Member', help = "Select if you want to give free membership."),
        'membership_amount': fields.float(
                    'Membership Amount', digits=(16, 2),
                    help = 'The price negotiated by the partner'),
        'membership_state': fields.function(
                    __get_membership_state,
                    string = 'Current Membership Status', type = 'selection',
                    selection = STATE,
                    store = {
                        'account.invoice': (_get_invoice_partner, ['state', 'invoice_line_ids', 'payment_ids'], 20),
                        'membership.membership_line': (_get_partner_id, ['state'], 20),
                        'res.partner': (_get_partners, ['free_member', 'membership_state', 'associate_member'], 20)
                    }, help='It indicates the membership state.\n'
                            '-Non Member: A partner who has not applied for any membership.\n'
                            '-Cancelled Member: A member who has cancelled his membership.\n'
                            '-Old Member: A member whose membership date has expired.\n'
                            '-Waiting Member: A member who has applied for the membership and whose invoice is going to be created.\n'
                            '-Invoiced Member: A member whose invoice has been created.\n'
                            '-Paying member: A member who has paid the membership fee.'),
        'membership_start': fields.function(
                    _membership_date,
                    string = 'Membership Start Date', type = 'date', multi='_membership_date',
                    store = {
                        'account.invoice': (_get_invoice_partner, ['state', 'invoice_line_ids', 'payment_ids'], 10),
                        'membership.membership_line': (_get_partner_id, ['state'], 10, ),
                        'res.partner': (_get_partners, ['free_member', 'membership_state', 'associate_member'], 10)
                    }, help="Date from which membership becomes active."),
        'membership_stop': fields.function(
                    _membership_date,
                    string = 'Membership End Date', type='date', multi='_membership_date',
                    store = {
                        'account.invoice': (_get_invoice_partner, ['state', 'invoice_line_ids', 'payment_ids'], 10),
                        'membership.membership_line': (_get_partner_id, ['state'], 10),
                        'res.partner': (_get_partners, ['free_member', 'membership_state', 'associate_member'], 10)
                    }, help="Date until which membership remains active."),
        'membership_cancel': fields.function(
                    _membership_date,
                    string = 'Cancel Membership Date', type='date', multi='_membership_date',
                    store = {
                        'account.invoice': (_get_invoice_partner, ['state', 'invoice_line_ids', 'payment_ids'], 11),
                        'membership.membership_line': (_get_partner_id, ['state'], 10),
                        'res.partner': (_get_partners, ['free_member', 'membership_state', 'associate_member'], 10)
                    }, help="Date on which membership has been cancelled"),
    }

    def _check_recursion(self, cr, uid, ids, context=None):
        """Check  Recursive  for Associated Members.
        """
        level = 100
        while len(ids):
            cr.execute('SELECT DISTINCT associate_member FROM res_partner WHERE id IN %s', (tuple(ids),))
            ids = filter(None, map(lambda x:x[0], cr.fetchall()))
            if not level:
                return False
            level -= 1
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive associated members.', ['associate_member'])
    ]

    def create_membership_invoice(self, cr, uid, ids, product_id=None, datas=None, context=None):
        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        product_id = product_id or datas.get('membership_product_id', False)
        amount = datas.get('amount', 0.0)
        invoice_list = []
        if type(ids) in (int, long,):
            ids = [ids]
        for partner in self.browse(cr, uid, ids, context=context):
            account_id = partner.property_account_receivable_id and partner.property_account_receivable_id.id or False
            fpos_id = partner.property_account_position_id and partner.property_account_position_id.id or False
            addr = self.address_get(cr, uid, [partner.id], ['invoice'])
            if partner.free_member:
                raise UserError(_("Partner is a free Member."))
            if not addr.get('invoice', False):
                raise UserError(_("Partner doesn't have an address to make the invoice."))
            invoice_values = {
                'partner_id': partner.id,
                'account_id': account_id,
                'fiscal_position_id': fpos_id or False
            }
            invoice_id = invoice_obj.create(cr, uid, invoice_values, context=context)
            line_values = {
                'product_id': product_id,
                'price_unit': amount,
                'invoice_id': invoice_id,
            }
            # create a record in cache, apply onchange then revert back to a dictionnary
            invoice_line = invoice_line_obj.new(cr, uid, line_values, context=context)
            invoice_line._onchange_product_id()
            line_values = invoice_line._convert_to_write(invoice_line._cache)
            line_values['price_unit'] = amount
            invoice_obj.write(cr, uid, [invoice_id], {'invoice_line_ids': [(0, 0, line_values)]}, context=context)
            invoice_list.append(invoice_id)
            invoice_obj.compute_taxes(cr, uid, [invoice_id])

        return invoice_list


class Product(osv.osv):
    _inherit = 'product.template'

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        ModelData = self.pool['ir.model.data']
        if context is None:
            context = {}

        if ('product' in context) and (context['product']=='membership_product'):
            if view_type == 'form':
                view_id = ModelData.xmlid_to_res_id(
                    cr, user, 'membership.membership_products_form', context=context)
            else:
                view_id = ModelData.xmlid_to_res_id(
                    cr, user, 'membership.membership_products_tree', context=context)
        return super(Product,self).fields_view_get(cr, user, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

    _columns = {
        'membership': fields.boolean('Membership', help='Check if the product is eligible for membership.'),
        'membership_date_from': fields.date('Membership Start Date', help='Date from which membership becomes active.'),
        'membership_date_to': fields.date('Membership End Date', help='Date until which membership remains active.'),
    }

    _sql_constraints = [('membership_date_greater','check(membership_date_to >= membership_date_from)','Error ! Ending Date cannot be set before Beginning Date.')]



class Invoice(osv.osv):
    _inherit = 'account.invoice'

    def action_cancel(self, cr, uid, ids, context=None):
        '''Create a 'date_cancel' on the membership_line object'''
        member_line_obj = self.pool.get('membership.membership_line')
        today = time.strftime('%Y-%m-%d')
        for invoice in self.browse(cr, uid, ids, context=context):
            mlines = member_line_obj.search(cr, uid,
                    [('account_invoice_line', 'in',
                        [l.id for l in invoice.invoice_line_ids])])
            member_line_obj.write(cr, uid, mlines, {'date_cancel': today})
        return super(Invoice, self).action_cancel(cr, uid, ids, context=context)

    # TODO master: replace by ondelete='cascade'
    def unlink(self, cr, uid, ids, context=None):
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.browse(cr, uid, ids, context=context):
            mlines = member_line_obj.search(cr, uid,
                    [('account_invoice_line', 'in',
                        [l.id for l in invoice.invoice_line_ids])])
            member_line_obj.unlink(cr, uid, mlines, context=context)
        return super(Invoice, self).unlink(cr, uid, ids, context=context)


class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    def write(self, cr, uid, ids, vals, context=None):
        """Overrides orm write method
        """
        member_line_obj = self.pool.get('membership.membership_line')
        res = super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)
        for line in self.browse(cr, uid, ids, context=context):
            if line.invoice_id.type == 'out_invoice':
                ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line', '=', line.id)], context=context)
                if line.product_id and line.product_id.membership and not ml_ids:
                    # Product line has changed to a membership product
                    date_from = line.product_id.membership_date_from
                    date_to = line.product_id.membership_date_to
                    if line.invoice_id.date_invoice > date_from and line.invoice_id.date_invoice < date_to:
                        date_from = line.invoice_id.date_invoice
                    member_line_obj.create(cr, uid, {
                                    'partner': line.invoice_id.partner_id.id,
                                    'membership_id': line.product_id.id,
                                    'member_price': line.price_unit,
                                    'date': time.strftime('%Y-%m-%d'),
                                    'date_from': date_from,
                                    'date_to': date_to,
                                    'account_invoice_line': line.id,
                                    }, context=context)
                if line.product_id and not line.product_id.membership and ml_ids:
                    # Product line has changed to a non membership product
                    member_line_obj.unlink(cr, uid, ml_ids, context=context)
        return res

    # TODO master: replace by ondelete='cascade'
    def unlink(self, cr, uid, ids, context=None):
        """Remove Membership Line Record for Account Invoice Line
        """
        member_line_obj = self.pool.get('membership.membership_line')
        for id in ids:
            ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line', '=', id)], context=context)
            member_line_obj.unlink(cr, uid, ml_ids, context=context)
        return super(account_invoice_line, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        """Overrides orm create method
        """
        member_line_obj = self.pool.get('membership.membership_line')
        result = super(account_invoice_line, self).create(cr, uid, vals, context=context)
        line = self.browse(cr, uid, result, context=context)
        if line.invoice_id.type == 'out_invoice':
            ml_ids = member_line_obj.search(cr, uid, [('account_invoice_line', '=', line.id)], context=context)
            if line.product_id and line.product_id.membership and not ml_ids:
                # Product line is a membership product
                date_from = line.product_id.membership_date_from
                date_to = line.product_id.membership_date_to
                if line.invoice_id.date_invoice > date_from and line.invoice_id.date_invoice < date_to:
                    date_from = line.invoice_id.date_invoice
                values = {
                            'partner': line.invoice_id.partner_id and line.invoice_id.partner_id.id or False,
                            'membership_id': line.product_id.id,
                            'member_price': line.price_unit,
                            'date': time.strftime('%Y-%m-%d'),
                            'date_from': date_from,
                            'date_to': date_to,
                            'account_invoice_line': line.id,
                        }
                member_line_obj.create(cr, uid, values, context=context)
        return result
