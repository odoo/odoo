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
from osv import fields, osv, orm
from tools.translate import _
import netsvc
import time

#----------------------------------------------------------
# Auction Artists
#----------------------------------------------------------

class auction_artists(osv.osv):
    _name = "auction.artists"
    _columns = {
        'name': fields.char('Artist/Author Name', size=64, required=True),
        'pseudo': fields.char('Pseudo', size=64),
        'birth_death_dates':fields.char('Lifespan', size=64),
        'biography': fields.text('Biography'),
    }
auction_artists()

#----------------------------------------------------------
# Auction Dates
#----------------------------------------------------------
class auction_dates(osv.osv):
    """Auction Dates"""
    _name = "auction.dates"
    _description=__doc__

    def _adjudication_get(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res={}
        total = 0.0
        lots_obj = self.pool.get('auction.lots')
        for auction in self.browse(cr, uid, ids):
            lots_ids = lots_obj.search(cr, uid, [('auction_id', '=', auction.id)])
            for lots in lots_obj.browse(cr, uid, lots_ids):
                total+=lots.obj_price or 0.0
                res[auction.id]=total
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['name', 'auction1'], context=context)
        name = [(r['id'], '['+r['auction1']+'] '+ r['name']) for r in reads]
        return name

    def _get_invoice(self, cr, uid, ids, name, arg, context=None):
        lots_obj = self.pool.get('auction.lots')
        result = {}
        for data in self.browse(cr, uid, ids, context=context):
            buyer_inv_ids = []
            seller_inv_ids = []
            result[data.id] = {
                'seller_invoice_history': buyer_inv_ids,
                'buyer_invoice_history': seller_inv_ids,
            }
            lots_ids = lots_obj.search(cr, uid, [('auction_id','=',data.id)])
            for lot in lots_obj.browse(cr, uid, lots_ids, context=context):
                if lot.ach_inv_id:
                    buyer_inv_ids.append(lot.ach_inv_id.id)
                if lot.sel_inv_id:
                    seller_inv_ids.append(lot.sel_inv_id.id)
            result[data.id]['seller_invoice_history'] = seller_inv_ids
            result[data.id]['buyer_invoice_history'] = buyer_inv_ids
        return result

    _columns = {
        'name': fields.char('Auction Name', size=64, required=True),
        'expo1': fields.date('First Exposition Day', required=True, help="Beginning exposition date for auction"),
        'expo2': fields.date('Last Exposition Day', required=True, help="Last exposition date for auction"),
        'auction1': fields.date('First Auction Day', required=True, help="Start date of auction"),
        'auction2': fields.date('Last Auction Day', required=True, help="End date of auction"),
        'journal_id': fields.many2one('account.journal', 'Buyer Journal', required=True, help="Account journal for buyer"),
        'journal_seller_id': fields.many2one('account.journal', 'Seller Journal', required=True, help="Account journal for seller"),
        'buyer_costs': fields.many2many('account.tax', 'auction_buyer_taxes_rel', 'auction_id', 'tax_id', 'Buyer Costs', help="Account tax for buyer"),
        'seller_costs': fields.many2many('account.tax', 'auction_seller_taxes_rel', 'auction_id', 'tax_id', 'Seller Costs', help="Account tax for seller"),
        'acc_income': fields.many2one('account.account', 'Income Account', required=True),
        'acc_expense': fields.many2one('account.account', 'Expense Account', required=True),
        'adj_total': fields.function(_adjudication_get, string='Total Adjudication', store=True),
        'state': fields.selection((('draft', 'Draft'), ('closed', 'Closed')), 'State', select=1, readonly=True,
                                  help='When auction starts the state is \'Draft\'.\n At the end of auction, the state becomes \'Closed\'.'),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account', required=False),
        'buyer_invoice_history': fields.function(_get_invoice, relation='account.invoice', string="Buyer Invoice", type='many2many', multi=True),
        'seller_invoice_history': fields.function(_get_invoice, relation='account.invoice', string="Seller Invoice", type='many2many', multi=True),
    }

    _defaults = {
        'state': lambda *a: 'draft',
    }

    _order = "auction1 desc"

    def close(self, cr, uid, ids, context=None):
        """
        Close an auction date.

        Create invoices for all buyers and sellers.
        STATE ='close'

        RETURN: True
        """
        lots_obj = self.pool.get('auction.lots')
        lots_ids = lots_obj.search(cr, uid, [('auction_id', 'in', ids), ('state', '=', 'draft'), ('obj_price', '>', 0)])
        lots_obj.lots_invoice(cr, uid, lots_ids, {}, None)
        lots_ids2 = lots_obj.search(cr, uid, [('auction_id', 'in', ids), ('obj_price', '>', 0)])
        lots_obj.seller_trans_create(cr, uid, lots_ids2, {})
        self.write(cr, uid, ids, {'state': 'closed'}) #close the auction
        return True

auction_dates()

#----------------------------------------------------------
# Deposits
#----------------------------------------------------------
class auction_deposit(osv.osv):
    """Auction Deposit Border"""

    _name = "auction.deposit"
    _description=__doc__
    _order = "id desc"
    _columns = {
        'transfer' : fields.boolean('Transfer'),
        'name': fields.char('Depositer Inventory', size=64, required=True),
        'partner_id': fields.many2one('res.partner', 'Seller', required=True, change_default=True),
        'date_dep': fields.date('Deposit date', required=True),
        'method': fields.selection((('keep', 'Keep until sold'), ('decease', 'Decrease limit of 10%'), ('contact', 'Contact the Seller')), 'Withdrawned method', required=True),
        'tax_id': fields.many2one('account.tax', 'Expenses'),
        'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
        'info': fields.char('Description', size=64),
        'lot_id': fields.one2many('auction.lots', 'bord_vnd_id', 'Objects'),
        'specific_cost_ids': fields.one2many('auction.deposit.cost', 'deposit_id', 'Specific Costs'),
        'total_neg': fields.boolean('Allow Negative Amount'),
    }
    _defaults = {
        'method': lambda *a: 'keep',
        'total_neg': lambda *a: False,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'auction.deposit'),
    }

auction_deposit()

#----------------------------------------------------------
# (Specific) Deposit Costs
#----------------------------------------------------------
class auction_deposit_cost(osv.osv):

    """Auction Deposit Cost"""

    _name = 'auction.deposit.cost'
    _description=__doc__
    _columns = {
        'name': fields.char('Cost Name', required=True, size=64),
        'amount': fields.float('Amount'),
        'account': fields.many2one('account.account', 'Destination Account', required=True),
        'deposit_id': fields.many2one('auction.deposit', 'Deposit'),
    }
auction_deposit_cost()

#----------------------------------------------------------
# Lots Categories
#----------------------------------------------------------
class aie_category(osv.osv):

    _name="aie.category"
    _order = "name"
    _columns={
       'name': fields.char('Name', size=64, required=True),
       'code':fields.char('Code', size=64),
       'parent_id': fields.many2one('aie.category', 'Parent aie Category', ondelete='cascade'),
       'child_ids': fields.one2many('aie.category', 'parent_id', help="children aie category")
    }

    def name_get(self, cr, uid, ids, context=None):
        res = []
        if not ids:
            return res
        reads = self.read(cr, uid, ids, ['name', 'parent_id'], context=context)
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1] + ' / ' + name
            res.append((record['id'], name))
        return res

aie_category()

class auction_lot_category(osv.osv):
    """Auction Lots Category"""

    _name = 'auction.lot.category'
    _description=__doc__
    _columns = {
        'name': fields.char('Category Name', required=True, size=64),
        'priority': fields.float('Priority'),
        'active' : fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the auction lot category without removing it."),
        'aie_categ': fields.many2one('aie.category', 'Category', ondelete='cascade'),
    }
    _defaults = {
        'active' : lambda *a: 1,
    }
auction_lot_category()

#----------------------------------------------------------
# Lots
#----------------------------------------------------------
def _type_get(self, cr, uid, context=None):
    obj = self.pool.get('auction.lot.category')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['name'], context)
    res = [(r['name'], r['name']) for r in res]
    return res

class auction_lots(osv.osv):

    """Auction Object"""
    _name = "auction.lots"
    _order = "obj_num,lot_num,id"
    _description=__doc__

    def button_not_bought(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'unsold'})

    def button_taken_away(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'taken_away', 'ach_emp': True})

    def button_unpaid(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft'})

    def button_bought(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'sold'})

    def _getprice(self, cr, uid, ids, fields, args, context=None):
        """This Function compute amount total with tax for buyer and seller.
        @param ids: List of  auction lots's id
        @param name: List of function fields.
        @param context: A standard dictionary for contextual values
        @return: Dictionary of function fields value.
        """

        res = {}
        account_analytic_line_obj = self.pool.get('account.analytic.line')
        lots = self.browse(cr, uid, ids, context=context)
        pt_tax = self.pool.get('account.tax')
        for lot in lots:
            taxes = []
            for name in fields:
                res[lot.id] = {name: False}
                amount = lot.obj_price or 0.0
                result = 0.0
                if name == "buyer_price":
                    if lot.author_right:
                        taxes.append(lot.author_right)
                    if lot.auction_id:
                        taxes += lot.auction_id.buyer_costs
                    tax = pt_tax.compute_all(cr, uid, taxes, amount, 1)['taxes']
                    for t in tax:
                        result += t.get('amount', 0.0)
                    result += amount
                elif name == "seller_price":
                    if lot.bord_vnd_id.tax_id:
                        taxes.append(lot.bord_vnd_id.tax_id)
                    elif lot.auction_id and lot.auction_id.seller_costs:
                        taxes += lot.auction_id.seller_costs
                    tax = pt_tax.compute_all(cr, uid, taxes, amount, 1)['taxes']
                    for t in tax:
                        result += t.get('amount', 0.0)
                    result += amount
                elif name == "gross_revenue":
                    if lot.auction_id:
                        result = lot.buyer_price - lot.seller_price

                elif name == "net_revenue":
                    if lot.auction_id:
                        result = lot.buyer_price - lot.seller_price - lot.costs

                elif name == "gross_margin":
                    if ((lot.obj_price==0) and (lot.state=='draft')):
                        amount = lot.lot_est1
                    else:
                        amount = lot.obj_price
                    if amount > 0:
                        result = (lot.gross_revenue * 100) / amount
                        result = round(result,2)

                elif name == "net_margin":
                    if ((lot.obj_price==0) and (lot.state=='draft')):
                        amount = lot.lot_est1
                    else:
                        amount = lot.obj_price
                    if amount > 0:
                        result = (lot.net_revenue * 100) / amount
                        result = round(result,2)
                elif name == "costs":
                    # costs: Total credit of analytic account
                    # objects sold during this auction (excluding analytic lines that are in the analytic journal of the auction date)
                    #TOCHECK: Calculation OF Indirect Cost
                    som = 0.0
                    if lot.auction_id:
                        auct_id = lot.auction_id.id
                        lot_count = self.search(cr, uid, [('auction_id', '=', auct_id)], count=True)
                        line_ids = account_analytic_line_obj.search(cr, uid, [
                                    ('account_id', '=', lot.auction_id.account_analytic_id.id),
                                    ('journal_id', '<>', lot.auction_id.journal_id.id),
                                    ('journal_id', '<>', lot.auction_id.journal_seller_id.id)])
                        for r in lot.bord_vnd_id.specific_cost_ids:
                            som += r.amount
                        for line in account_analytic_line_obj.browse(cr, uid, line_ids, context=context):
                            if line.amount:
                                som -= line.amount
                        result = som/lot_count

                elif name=="paid_ach":
                    result = False
                    if lot.ach_inv_id and lot.ach_inv_id.state == 'paid':
                        result = True

                elif name=="paid_vnd":
                    result = False
                    if lot.sel_inv_id and lot.sel_inv_id.state == 'paid':
                        result = True

                res[lot.id][name] = result


        return res

    def onchange_obj_ret(self, cr, uid, ids, obj_ret, context=None):
        if obj_ret:
            return {'value': {'obj_price': 0}}
        return {}

    _columns = {
        'bid_lines':fields.one2many('auction.bid_line', 'lot_id', 'Bids'),
        'auction_id': fields.many2one('auction.dates', 'Auction', select=1, help="Auction for object"),
        'bord_vnd_id': fields.many2one('auction.deposit', 'Depositer Inventory', required=True, help="Provide deposit information: seller, Withdrawned Method, Object, Deposit Costs"),
        'name': fields.char('Title', size=64, required=True, help='Auction object name'),
        'name2': fields.char('Short Description (2)', size=64),
        'lot_type': fields.selection(_type_get, 'Object category', size=64),
        'author_right': fields.many2one('account.tax', 'Author rights', help="Account tax for author commission"),
        'lot_est1': fields.float('Minimum Estimation', help="Minimum Estimate Price"),
        'lot_est2': fields.float('Maximum Estimation', help="Maximum Estimate Price"),
        'lot_num': fields.integer('List Number', required=True, select=1, help="List number in depositer inventory"),
        'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
        'history_ids':fields.one2many('auction.lot.history', 'lot_id', 'Auction history'),
        'lot_local':fields.char('Location', size=64, help="Auction Location"),
        'artist_id':fields.many2one('auction.artists', 'Artist/Author'),
        'artist2_id':fields.many2one('auction.artists', 'Artist/Author2'),
        'important':fields.boolean('To be Emphatized'),
        'product_id':fields.many2one('product.product', 'Product', required=True),
        'obj_desc': fields.text('Object Description'),
        'obj_num': fields.integer('Catalog Number'),
        'obj_ret': fields.float('Price retired', help="Object Ret"),
        'obj_comm': fields.boolean('Commission'),
        'obj_price': fields.float('Adjudication price', help="Object Price"),
        'ach_avance': fields.float('Buyer Advance'),
        'ach_login': fields.char('Buyer Username', size=64),
        'ach_uid': fields.many2one('res.partner', 'Buyer'),
        'seller_id': fields.related('bord_vnd_id','partner_id', type='many2one', relation='res.partner', string='Seller', readonly=True),
        'ach_emp': fields.boolean('Taken Away', readonly=True, help="When state is Taken Away, this field is marked as True"),
        'is_ok': fields.boolean('Buyer\'s payment', help="When buyer pay for bank statement', this field is marked"),
        'ach_inv_id': fields.many2one('account.invoice', 'Buyer Invoice', readonly=True, states={'draft':[('readonly', False)]}),
        'sel_inv_id': fields.many2one('account.invoice', 'Seller Invoice', readonly=True, states={'draft':[('readonly', False)]}),
        'vnd_lim': fields.float('Seller limit'),
        'vnd_lim_net': fields.boolean('Net limit ?', readonly=True),
        'image': fields.binary('Image', help="Object Image"),
        'paid_vnd':fields.function(_getprice, string='Seller Paid', type='boolean', store=True, multi="paid_vnd", help="When state of Seller Invoice is 'Paid', this field is selected as True."),
        'paid_ach':fields.function(_getprice, string='Buyer Invoice Reconciled', type='boolean', store=True, multi="paid_ach", help="When state of Buyer Invoice is 'Paid', this field is selected as True."),
        'state': fields.selection((
            ('draft', 'Draft'),
            ('unsold', 'Unsold'),
            ('paid', 'Paid'),
            ('sold', 'Sold'),
            ('taken_away', 'Taken away')), 'State', required=True, readonly=True,
            help=' * The \'Draft\' state is used when a object is encoding as a new object. \
                \n* The \'Unsold\' state is used when object does not sold for long time, user can also set it as draft state after unsold. \
                \n* The \'Paid\' state is used when user pay for the object \
                \n* The \'Sold\' state is used when user buy the object.'),
        'buyer_price': fields.function(_getprice, string='Buyer price', store=True, multi="buyer_price", help="Buyer Price"),
        'seller_price': fields.function(_getprice, string='Seller price', store=True, multi="seller_price", help="Seller Price"),
        'gross_revenue':fields.function(_getprice, string='Gross revenue', store=True, multi="gross_revenue", help="Buyer Price - Seller Price"),
        'gross_margin':fields.function(_getprice, string='Gross Margin (%)', store=True, multi="gross_margin", help="(Gross Revenue*100.0)/ Object Price"),
        'costs':fields.function(_getprice, string='Indirect costs', store=True, multi="costs", help="Deposit cost"),
        'statement_id': fields.many2many('account.bank.statement.line', 'auction_statement_line_rel', 'auction_id', 'statement', 'Payment', help="Bank statement line for given buyer"),
        'net_revenue':fields.function(_getprice, string='Net revenue', store=True, multi="net_revenue", help="Buyer Price - Seller Price - Indirect Cost"),
        'net_margin':fields.function(_getprice, string='Net Margin (%)', store=True, multi="net_margin", help="(Net Revenue * 100)/ Object Price"),
    }
    _defaults = {
        'state':lambda *a: 'draft',
        'lot_num':lambda *a:1,
        'is_ok': lambda *a: False,
    }

    def name_get(self, cr, user, ids, context=None):
        if not ids:
            return []
        result = [ (r['id'], str(r['obj_num'])+' - '+r['name']) for r in self.read(cr, user, ids, ['name', 'obj_num'])]
        return result

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None):
        if not args:
            args = []
        ids = []
        if name:
            ids = self.search(cr, user, [('obj_num', '=', int(name))] + args)
        if not ids:
            ids = self.search(cr, user, [('name', operator, name)] + args)
        return self.name_get(cr, user, ids)

    def _sum_taxes_by_type_and_id(self, taxes):
        """
        PARAMS: taxes: a list of dictionaries of the form {'id':id, 'amount':amount, ...}
        RETURNS : a list of dictionaries of the form {'id':id, 'amount':amount, ...}; one dictionary per unique id.
            The others fields in the dictionaries (other than id and amount) are those of the first tax with a particular id.
        """
        taxes_summed = {}
        for tax in taxes:
            key = (tax['type'], tax['id'])
            if key in taxes_summed:
                taxes_summed[key]['amount'] += tax['amount']
            else:
                taxes_summed[key] = tax
        return taxes_summed.values()

    def compute_buyer_costs(self, cr, uid, ids):
        amount_total = {}
        lots = self.browse(cr, uid, ids)
        ##CHECKME: Is that AC would be worthwhile to make groups of lots that have the same costs to spend a lot of lists compute?
        taxes = []
        amount=0.0
        pt_tax = self.pool.get('account.tax')
        for lot in lots:
            taxes = lot.product_id.taxes_id
            if lot.author_right:
                taxes.append(lot.author_right)
            elif lot.auction_id:
                taxes += lot.auction_id.buyer_costs
            tax=pt_tax.compute_all(cr, uid, taxes, lot.obj_price, 1)['taxes']
            for t in tax:
                amount+=t['amount']
        amount_total['value']= amount
        amount_total['amount']= amount

        return amount_total


    def _compute_lot_seller_costs(self, cr, uid, lot, manual_only=False):
        costs = []
        tax_cost_ids=[]

        border_id = lot.bord_vnd_id
        if border_id:
            if border_id.tax_id:
                tax_cost_ids.append(border_id.tax_id)
            elif lot.auction_id and lot.auction_id.seller_costs:
                tax_cost_ids += lot.auction_id.seller_costs

        tax_costs = self.pool.get('account.tax').compute_all(cr, uid, tax_cost_ids, lot.obj_price, 1)['taxes']
        # delete useless keys from the costs computed by the tax object... this is useless but cleaner...
        for cost in tax_costs:
            del cost['account_paid_id']
            del cost['account_collected_id']

        if not manual_only:
            costs.extend(tax_costs)
            for c in costs:
                c.update({'type': 0})
######
        if lot.vnd_lim_net<0 and lot.obj_price>0:
            #FIXME:the string passes have lot 'should go through the system translations.
            obj_price_wh_costs = reduce(lambda x, y: x + y['amount'], tax_costs, lot.obj_price)
            if obj_price_wh_costs < lot.vnd_lim:
                costs.append({  'type': 1,
                                'id': lot.obj_num,
                                'name': 'Remise lot '+ str(lot.obj_num),
                                'amount': lot.vnd_lim - obj_price_wh_costs}
                            )
        return costs

    def compute_seller_costs(self, cr, uid, ids, manual_only=False):
        lots = self.browse(cr, uid, ids)
        costs = []

        # group objects (lots) by deposit id
        # ie create a dictionary containing lists of objects
        bord_lots = {}
        for lot in lots:
            key = lot.bord_vnd_id.id
            if not key in bord_lots:
                bord_lots[key] = []
            bord_lots[key].append(lot)

        # use each list of object in turn
        for lots in bord_lots.values():
            total_adj = 0
            total_cost = 0
            for lot in lots:
                total_adj += lot.obj_price or 0.0
                lot_costs = self._compute_lot_seller_costs(cr, uid, lot, manual_only)
                for c in lot_costs:
                    total_cost += c['amount']
                costs.extend(lot_costs)
            bord = lots[0].bord_vnd_id
            if bord:
                if bord.specific_cost_ids:
                    bord_costs = [{'type':2, 'id':c.id, 'name':c.name, 'amount':c.amount, 'account_id':c.account} for c in bord.specific_cost_ids]
                    for c in bord_costs:
                        total_cost += c['amount']
                    costs.extend(bord_costs)
            if (total_adj+total_cost)<0:
                #FIXME: translate tax name
                new_id = bord and bord.id or 0
                c = {'type':3, 'id':new_id, 'amount':-total_cost-total_adj, 'name':'Ristourne'}
                costs.append(c)
        return self._sum_taxes_by_type_and_id(costs)

    # sum remise limite net and ristourne
    def compute_seller_costs_summed(self, cr, uid, ids): #ach_pay_id

        """This Fuction  sum Net remittance limit and refund"""

        taxes = self.compute_seller_costs(cr, uid, ids)
        taxes_summed = {}
        for tax in taxes:
            if tax['type'] == 1:
                tax['id'] = 0
                #FIXME: translate tax names
                tax['name'] = 'Discount sharp boundary'
            elif tax['type'] == 2:
                tax['id'] = 0
                tax['name'] = 'Miscellaneous expenditure'
            elif tax['type'] == 3:
                tax['id'] = 0
                tax['name'] = 'Cross.'
            key = (tax['type'], tax['id'])
            if key in taxes_summed:
                taxes_summed[key]['amount'] += tax['amount']
            else:
                taxes_summed[key] = tax
        return taxes_summed.values()

    def buyer_proforma(self, cr, uid, ids, context=None):

        invoices = {}
        inv_ref = self.pool.get('account.invoice')
        res_obj = self.pool.get('res.partner')
        inv_line_obj = self.pool.get('account.invoice.line')
        wf_service = netsvc.LocalService('workflow')
        for lot in self.browse(cr, uid, ids, context=context):
            if not lot.obj_price>0:
                continue
            if not lot.ach_uid.id:
                raise orm.except_orm(_('Missed buyer !'), _('The object "%s" has no buyer assigned.') % (lot.name,))
            else:
                partner_ref =lot.ach_uid.id
                res = res_obj.address_get(cr, uid, [partner_ref], ['contact', 'invoice'])
                contact_addr_id = res['contact']
                invoice_addr_id = res['invoice']
                if not invoice_addr_id:
                    raise orm.except_orm(_('No Invoice Address'), _('The Buyer "%s" has no Invoice Address.') % (contact_addr_id,))
                inv = {
                    'name': 'Auction proforma:' +lot.name,
                    'journal_id': lot.auction_id.journal_id.id,
                    'partner_id': partner_ref,
                    'type': 'out_invoice',
                }
                inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', partner_ref)['value'])
                inv['account_id'] = inv['account_id'] and inv['account_id'][0]
                inv_id = inv_ref.create(cr, uid, inv, context)
                invoices[partner_ref] = inv_id
                self.write(cr, uid, [lot.id], {'ach_inv_id':inv_id, 'state':'sold'})

                #calcul des taxes
                taxes = map(lambda x: x.id, lot.product_id.taxes_id)
                taxes+=map(lambda x:x.id, lot.auction_id.buyer_costs)
                if lot.author_right:
                    taxes.append(lot.author_right.id)

                inv_line= {
                    'invoice_id': inv_id,
                    'quantity': 1,
                    'product_id': lot.product_id.id,
                    'name': 'proforma'+'['+str(lot.obj_num)+'] '+ lot.name,
                    'invoice_line_tax_id': [(6, 0, taxes)],
                    'account_analytic_id': lot.auction_id.account_analytic_id.id,
                    'account_id': lot.auction_id.acc_income.id,
                    'price_unit': lot.obj_price,
                }
                inv_line_obj.create(cr, uid, inv_line, context)
            inv_ref.button_compute(cr, uid, invoices.values())
            wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_proforma2', cr)
        return invoices.values()

    # creates the transactions between the auction company and the seller
    # this is done by creating a new in_invoice for each
    def seller_trans_create(self, cr, uid, ids, context=None):
        """
            Create a seller invoice for each bord_vnd_id, for selected ids.
        """
        # use each list of object in turn
        invoices = {}
        inv_ref=self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        wf_service = netsvc.LocalService('workflow')
        for lot in self.browse(cr, uid, ids, context=context):
            if not lot.auction_id.id:
                continue
            if lot.bord_vnd_id.id in invoices:
                inv_id = invoices[lot.bord_vnd_id.id]
            else:
                inv = {
                    'name': 'Auction:' +lot.name,
                    'journal_id': lot.auction_id.journal_seller_id.id,
                    'partner_id': lot.bord_vnd_id.partner_id.id,
                    'type': 'in_invoice',
                }
                inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'in_invoice', lot.bord_vnd_id.partner_id.id)['value'])
                inv_id = inv_ref.create(cr, uid, inv, context)
                invoices[lot.bord_vnd_id.id] = inv_id

            self.write(cr, uid, [lot.id], {'sel_inv_id':inv_id, 'state':'sold'})

            taxes = map(lambda x: x.id, lot.product_id.taxes_id)
            if lot.bord_vnd_id.tax_id:
                taxes.append(lot.bord_vnd_id.tax_id.id)
            else:
                taxes += map(lambda x: x.id, lot.auction_id.seller_costs)

            inv_line= {
                'invoice_id': inv_id,
                'quantity': 1,
                'product_id': lot.product_id.id,
                'name': '['+str(lot.obj_num)+'] '+lot.auction_id.name,
                'invoice_line_tax_id': [(6, 0, taxes)],
                'account_analytic_id': lot.auction_id.account_analytic_id.id,
                'account_id': lot.auction_id.acc_expense.id,
                'price_unit': lot.obj_price,
            }
            inv_line_obj.create(cr, uid, inv_line, context)
            inv_ref.button_compute(cr, uid, invoices.values())
        for inv in inv_ref.browse(cr, uid, invoices.values(), context=context):
            inv_ref.write(cr, uid, [inv.id], {
                'check_total': inv.amount_total
            })
            wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_open', cr)
        return invoices.values()

    def lots_invoice(self, cr, uid, ids, context, invoice_number=False):
        """(buyer invoice
            Create an invoice for selected lots (IDS) to BUYER_ID.
            Set created invoice to the ACTION state.
            PRE:
                ACTION:
                    False: no action
                    xxxxx: set the invoice state to ACTION

            RETURN: id of generated invoice
        """
        inv_ref = self.pool.get('account.invoice')
        res_obj = self.pool.get('res.partner')
        inv_line_obj = self.pool.get('account.invoice.line')
        wf_service = netsvc.LocalService('workflow')
        invoices={}
        for lot in self.browse(cr, uid, ids, context):
            if not lot.auction_id.id:
                continue
            if not lot.ach_uid.id:
                raise orm.except_orm(_('Missed buyer !'), _('The object "%s" has no buyer assigned.') % (lot.name,))
            if (lot.auction_id.id, lot.ach_uid.id) in invoices:
                inv_id = invoices[(lot.auction_id.id, lot.ach_uid.id)]
            else:
                add = res_obj.read(cr, uid, [lot.ach_uid.id], ['address'])[0]['address']
                if not len(add):
                    raise orm.except_orm(_('Missed Address !'), _('The Buyer has no Invoice Address.'))
                inv = {
                    'name':lot.auction_id.name or '',
                    'reference': lot.ach_login,
                    'journal_id': lot.auction_id.journal_id.id,
                    'partner_id': lot.ach_uid.id,
                    'type': 'out_invoice',
                }
                if invoice_number:
                    inv['number'] = invoice_number
                inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', lot.ach_uid.id)['value'])
                inv_id = inv_ref.create(cr, uid, inv, context)
                invoices[(lot.auction_id.id, lot.ach_uid.id)] = inv_id
            self.write(cr, uid, [lot.id], {'ach_inv_id':inv_id, 'state':'sold'})
            #calcul des taxes
            taxes = map(lambda x: x.id, lot.product_id.taxes_id)
            taxes+=map(lambda x:x.id, lot.auction_id.buyer_costs)
            if lot.author_right:
                taxes.append(lot.author_right.id)

            inv_line= {
                'invoice_id': inv_id,
                'quantity': 1,
                'product_id': lot.product_id.id,
                'name': '['+str(lot.obj_num)+'] '+ lot.name,
                'invoice_line_tax_id': [(6, 0, taxes)],
                'account_analytic_id': lot.auction_id.account_analytic_id.id,
                'account_id': lot.auction_id.acc_income.id,
                'price_unit': lot.obj_price,
            }
            inv_line_obj.create(cr, uid, inv_line, context)
            inv_ref.button_compute(cr, uid, [inv_id])
        for l in  inv_ref.browse(cr, uid, invoices.values(), context):
            wf_service.trg_validate(uid, 'account.invoice', l.id, 'invoice_open', cr)
        return invoices.values()

auction_lots()

#----------------------------------------------------------
# Auction Bids
#----------------------------------------------------------
class auction_bid(osv.osv):
    """Bid Auctions"""

    _name = "auction.bid"
    _description=__doc__
    _order = 'id desc'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Buyer Name', required=True),
        'contact_tel':fields.char('Contact Number', size=64),
        'name': fields.char('Bid ID', size=64, required=True),
        'auction_id': fields.many2one('auction.dates', 'Auction Date', required=True),
        'bid_lines': fields.one2many('auction.bid_line', 'bid_id', 'Bid'),
    }
    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'auction.bid'),
    }

    def onchange_contact(self, cr, uid, ids, partner_id):
        if not partner_id:
            return {'value': {'contact_tel':False}}
        contact = self.pool.get('res.partner').browse(cr, uid, partner_id)
        if len(contact.address):
            v_contact=contact.address[0] and contact.address[0].phone
        else:
            v_contact = False
        return {'value': {'contact_tel': v_contact}}

auction_bid()

class auction_lot_history(osv.osv):
    """Lot History"""

    _name = "auction.lot.history"
    _description=__doc__
    _columns = {
        'name': fields.date('Date', size=64),
        'lot_id': fields.many2one('auction.lots', 'Object', required=True, ondelete='cascade'),
        'auction_id': fields.many2one('auction.dates', 'Auction date', required=True, ondelete='cascade'),
        'price': fields.float('Withdrawn price', digits=(16, 2))
    }
    _defaults = {
        'name': lambda *args: time.strftime('%Y-%m-%d')
    }
auction_lot_history()

class auction_bid_lines(osv.osv):
    _name = "auction.bid_line"
    _description="Bid"

    _columns = {
        'name': fields.char('Bid date', size=64),
        'bid_id': fields.many2one('auction.bid', 'Bid ID', required=True, ondelete='cascade'),
        'lot_id': fields.many2one('auction.lots', 'Object', required=True, ondelete='cascade'),
        'call': fields.boolean('To be Called'),
        'price': fields.float('Maximum Price'),
        'auction': fields.char(string='Auction Name', size=64)
    }
    _defaults = {
        'name': lambda *args: time.strftime('%Y-%m-%d')
    }

    def onchange_name(self, cr, uid, ids, lot_id):
        if not lot_id:
            return {'value': {'auction':False}}
        auctions = self.pool.get('auction.lots').browse(cr, uid, lot_id)
        v_auction=auctions.auction_id.name or False
        return {'value': {'auction': v_auction}}


auction_bid_lines()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
