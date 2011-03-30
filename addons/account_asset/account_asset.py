# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
import time
class account_asset_category(osv.osv):
    _name = 'account.asset.category'
    _description = 'Asset category'
    _columns = {
        'name': fields.char('Asset category', size=64, required=True, select=1),
        'code': fields.char('Reference', size=16, select=1),
        'note': fields.text('Note'),
	'name': fields.char('Method name', size=64, select=1),
        'type': fields.selection([('direct','Direct'),('indirect','Indirect')], 'Depr. method type', select=2, required=True),
        'asset_id': fields.many2one('account.asset.asset', 'Asset', required=True),
        'account_asset_id': fields.many2one('account.account', 'Asset account', required=True),
        'account_actif_id': fields.many2one('account.account', 'Depreciation account', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),

	
    }
account_asset_category()


class account_asset_asset(osv.osv):
    _name = 'account.asset.asset'
    _description = 'Asset'

#   def _balance(self, cr, uid, ids, field_name, arg, context={}):
#       acc_set = ",".join(map(str, ids))
#       query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
#       cr.execute(("SELECT a.id, COALESCE(SUM((l.debit-l.credit)),0) FROM account_asset_asset a LEFT JOIN account_move_line l ON (a.id=l.asset_account_id) WHERE a.id IN (%s) and "+query+" GROUP BY a.id") % (acc_set,))
#       res = {}
#       for account_id, sum in cr.fetchall():
#           res[account_id] = round(sum,2)
#       for id in ids:
#           res[id] = round(res.get(id,0.0), 2)
#       return res
    def _get_period(self, cr, uid, context={}):
        periods = self.pool.get('account.period').find(cr, uid)
        if periods:
            return periods[0]
        else:
            return False

    def validate(self, cr, uid, ids, context={}):
        for asset in self.browse(cr, uid, ids, context):
            for prop in asset.property_ids:
                if prop.state=='draft':
                    self.pool.get('account.asset.property').write(cr, uid, [prop.id], {'state':'open'}, context)
        return self.write(cr, uid, ids, {
            'state':'normal'
        }, context)

    def _amount_total(self, cr, uid, ids, name, args, context={}):
        id_set=",".join(map(str,ids))
        cr.execute("""SELECT l.asset_id,abs(SUM(l.debit-l.credit)) AS amount FROM 
                account_move_line l
            WHERE l.asset_id IN ("""+id_set+") GROUP BY l.asset_id ")
        res=dict(cr.fetchall())
        for id in ids:
            res.setdefault(id, 0.0)
        return res
    _columns = {
        'name': fields.char('Asset', size=64, required=True, select=1),
        'code': fields.char('Reference ', size=16, select=1),
	'purch_valu': fields.float('Purchase value ', required=True, size=16, select=1),
	'currency': fields.many2one('res.currency','Currency',required=True,size=5,select=1),
	'company': fields.char('Company',size=16, select=1),
        'note': fields.text('Note'),
        'category_id': fields.many2one('account.asset.category', 'Asset category',required=True, change_default=True),
        'localisation': fields.char('Localisation', size=32, select=2),
        'sequence': fields.integer('Sequence'),
        'parent_id': fields.many2one('account.asset.asset', 'Parent asset'),
        'child_ids': fields.one2many('account.asset.asset', 'parent_id', 'Child assets'),
        'date': fields.date('Date', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('view','View'),('draft','Draft'),('normal','Normal'),('close','Close')], 'Global state', required=True),
        'active': fields.boolean('Active', select=2),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'entry_ids': fields.one2many('account.move.line', 'asset_id', 'Entries', readonly=True, states={'draft':[('readonly',False)]}),
        'property_ids': fields.one2many('account.asset.property', 'asset_id', 'Asset method name', readonly=True, states={'draft':[('readonly',False)]}),
        'value_total': fields.function(_amount_total, method=True, digits=(16,2),string='Total value'),
 	'test': fields.one2many('account.move.line', 'asset_id', 'Entries', readonly=True, states={'draft':[('readonly',False)]}),

    }
    _defaults = {
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'account.asset.code'),
        'date': lambda obj, cr, uid, context: time.strftime('%Y-%m-%d'),
        'active': lambda obj, cr, uid, context: True,
        'state': lambda obj, cr, uid, context: 'draft',
        'period_id': _get_period,
    }
    def _compute_period(self, cr, uid, property, context={}):
        if (len(property.entry_asset_ids or [])/2)>=property.method_delay:
            return False
        if len(property.entry_asset_ids):
            cp = property.entry_asset_ids[-1].period_id
            cpid = self.pool.get('account.period').next(cr, uid, cp, property.method_period, context)
            current_period = self.pool.get('account.period').browse(cr, uid, cpid, context)
        else:
            current_period = property.asset_id.period_id
        return current_period

    def _compute_move(self, cr, uid, property, period, context={}):
        result = []
        total = 0.0
        for move in property.asset_id.entry_ids:
            total += move.debit-move.credit
        for move in property.entry_asset_ids:
            if move.account_id == property.account_asset_ids:
                total += move.debit
                total += -move.credit
        periods = (len(property.entry_asset_ids)/2) - property.method_delay
        if periods==1:
            amount = total
        else:
            if property.method == 'linear':
                amount = total / periods
            else:
                amount = total * property.method_progress_factor

        move_id = self.pool.get('account.move').create(cr, uid, {
            'journal_id': property.journal_id.id,
            'period_id': period.id,
            'name': property.name or property.asset_id.name,
            'ref': property.asset_id.code
        })
        result = [move_id]
        id = self.pool.get('account.move.line').create(cr, uid, {
            'name': property.name or property.asset_id.name,
            'move_id': move_id,
            'account_id': property.account_asset_id.id,
            'debit': amount>0 and amount or 0.0,
            'credit': amount<0 and -amount or 0.0,
            'ref': property.asset_id.code,
            'period_id': period.id,
            'journal_id': property.journal_id.id,
            'partner_id': property.asset_id.partner_id.id,
            'date': time.strftime('%Y-%m-%d'),
        })
        id2 = self.pool.get('account.move.line').create(cr, uid, {
            'name': property.name or property.asset_id.name,
            'move_id': move_id,
            'account_id': property.account_actif_id.id,
            'credit': amount>0 and amount or 0.0,
            'debit': amount<0 and -amount or 0.0,
            'ref': property.asset_id.code,
            'period_id': period.id,
            'journal_id': property.journal_id.id,
            'partner_id': property.asset_id.partner_id.id,
            'date': time.strftime('%Y-%m-%d'),
        })
        self.pool.get('account.asset.property').write(cr, uid, [property.id], {
            'entry_asset_ids': [(4, id2, False),(4,id,False)]
        })
        if property.method_delay - (len(property.entry_asset_ids)/2)<=1:
            self.pool.get('account.asset.property')._close(cr, uid, property, context)
            return result
        return result

    def _compute_entries(self, cr, uid, asset, period_id, context={}):
        result = []
        date_start = self.pool.get('account.period').browse(cr, uid, period_id, context).date_start
        for property in asset.property_ids:
            if property.state=='open':
                period = self._compute_period(cr, uid, property, context)
                if period and (period.date_start<=date_start):
                    result += self._compute_move(cr, uid, property, period, context)
        return result
account_asset_asset()

class account_asset_property(osv.osv):
    def _amount_total(self, cr, uid, ids, name, args, context={}):
        id_set=",".join(map(str,ids))
        cr.execute("""SELECT l.asset_id,abs(SUM(l.debit-l.credit)) AS amount FROM 
                account_asset_property p
            left join
                account_move_line l on (p.asset_id=l.asset_id)
            WHERE p.id IN ("""+id_set+") GROUP BY l.asset_id ")
        res=dict(cr.fetchall())
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def _amount_residual(self, cr, uid, ids, name, args, context={}):
        id_set=",".join(map(str,ids))
        cr.execute("""SELECT 
                r.asset_property_id,SUM(abs(l.debit-l.credit)) AS amount
            FROM
                account_move_asset_entry_rel r
            LEFT JOIN
                account_move_line l on (r.move_id=l.id)
            WHERE
                r.asset_property_id IN ("""+id_set+") GROUP BY r.asset_property_id ")
        res=dict(cr.fetchall())
        for prop in self.browse(cr, uid, ids, context):
            res[prop.id] = prop.value_total - res.get(prop.id, 0.0)
        for id in ids:
            res.setdefault(id, 0.0)
        return res

    def _close(self, cr, uid, property, context={}):
        if property.state<>'close':
            self.pool.get('account.asset.property').write(cr, uid, [property.id], {
                'state': 'close'
            })
            property.state='close'
        ok = property.asset_id.state=='open'
        for prop in property.asset_id.property_ids:
            ok = ok and prop.state=='close'
        self.pool.get('account.asset.asset').write(cr, uid, [property.asset_id.id], {
            'state': 'close'
        }, context)
        return True

    _name = 'account.asset.property'
    _description = 'Asset property'
    _columns = {
        'name': fields.char('Method name', size=64, select=1),
        'type': fields.selection([('direct','Direct'),('indirect','Indirect')], 'Depr. method type', select=2, required=True),
        'asset_id': fields.many2one('account.asset.asset', 'Asset', required=True),
        'account_asset_id': fields.many2one('account.account', 'Asset account', required=True),
        'account_actif_id': fields.many2one('account.account', 'Depreciation account', required=True),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
        'journal_analytic_id': fields.many2one('account.analytic.journal', 'Analytic journal'),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic account'),

        'method': fields.selection([('linear','Linear'),('progressif','Progressive')], 'Computation method', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'method_progress_factor': fields.float('Progressif factor', readonly=True, states={'draft':[('readonly',False)]}),
        'method_time': fields.selection([('delay','Delay'),('end','Ending period')], 'Time method', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'method_delay': fields.integer('During', readonly=True, states={'draft':[('readonly',False)]}),
        'method_period': fields.integer('Depre. all', readonly=True, states={'draft':[('readonly',False)]}),
        'method_end': fields.date('Ending date'),
	'prorata':fields.boolean('Prorata Temporis', Readonly="True", help='Si l amortissement se realise après le 1 janvier'),

        'date': fields.date('Date created'),
	#'test': fields.one2many('account.pre', 'asset_id',  readonly=True, states={'draft':[('readonly',False)]}),
        'entry_asset_ids': fields.many2many('account.move.line', 'account_move_asset_entry_rel', 'asset_property_id', 'move_id', 'Asset Entries'),
        'board_ids': fields.one2many('account.asset.board', 'asset_id', 'Asset board'),

        'value_total': fields.function(_amount_total, method=True, digits=(16,2),string='Gross value'),
        'value_residual': fields.function(_amount_residual, method=True, digits=(16,2), string='Residual value'),
        'state': fields.selection([('draft','Draft'), ('open','Open'), ('close','Close')], 'State', required=True),
        'history_ids': fields.one2many('account.asset.property.history', 'asset_property_id', 'History', readonly=True)
#	'parent_id': fields.many2one('account.asset.asset', 'Parent asset'),
#	'partner_id': fields.many2one('res.partner', 'Partner'),
#	'note': fields.text('Note'),

    }
    _defaults = {
        'type': lambda obj, cr, uid, context: 'direct',
        'state': lambda obj, cr, uid, context: 'draft',
        'method': lambda obj, cr, uid, context: 'linear',
        'method_time': lambda obj, cr, uid, context: 'delay',
        'method_progress_factor': lambda obj, cr, uid, context: 0.3,
        'method_delay': lambda obj, cr, uid, context: 5,
        'method_period': lambda obj, cr, uid, context: 12,
        'date': lambda obj, cr, uid, context: time.strftime('%Y-%m-%d')
    }
account_asset_property()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'
    _columns = {
        'asset_id': fields.many2one('account.asset.asset', 'Asset'),
        'entry_ids': fields.one2many('account.move.line', 'asset_id', 'Entries', readonly=True, states={'draft':[('readonly',False)]}),	

    }
account_move_line()




class account_pre(osv.osv):
    _name = 'account.pre'
    _columns = {
        'name': fields.char('Test',size=64, select=1),
        'asset_id': fields.many2one('account.asset.asset','Asset'),
 #       'test': fields.one2many('account.pre','asset_id','test', readonly=True,states={'draft':[('readonly',False)]}),
    }
account_pre()



class account_asset_property_history(osv.osv):
    _name = 'account.asset.property.history'
    _description = 'Asset history'
    _columns = {
        'name': fields.char('History name', size=64, select=1),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'date': fields.date('Date', required=True),
        'asset_property_id': fields.many2one('account.asset.property', 'Method', required=True),
        'method_delay': fields.integer('Number of interval'),
        'method_period': fields.integer('Period per interval'),
        'method_end': fields.date('Ending date'),
        'note': fields.text('Note'),
    }
    _defaults = {
        'date': lambda *args: time.strftime('%Y-%m-%d'),
        'user_id': lambda self,cr, uid,ctx: uid
    }
account_asset_property_history()


class account_asset_board(osv.osv):
    _name = 'account.asset.board'
    _description = 'Asset board'
    _columns = {
        'name': fields.char('Asset name', size=64, required=True, select=1),
        'asset_id': fields.many2one('account.asset.property', 'Asset', required=True, select=1),
        'value_gross': fields.float('Gross value', required=True, select=1),
        'value_asset': fields.float('Asset Value', required=True, select=1),
        'value_asset_cumul': fields.float('Cumul. value', required=True, select=1),
        'value_net': fields.float('Net value', required=True, select=1),

    }
    _auto = False
    def init(self, cr):
        cr.execute("""
            create or replace view account_asset_board as (
                select
                    min(l.id) as id,
                    min(l.id) as asset_id,
                    0.0 as value_gross,
                    0.0 as value_asset,
                    0.0 as value_asset_cumul,
                    0.0 as value_net
                from
                    account_move_line l
                where
                    l.state <> 'draft' and
                    l.asset_id=3
            )""")
account_asset_board()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

