# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
import logging
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)


class law_trust_journal(models.Model):
	_inherit = 'account.journal'

	type = fields.Selection([('sale', 'Sale'),('sale_refund','Sale Refund'), ('purchase', 'Purchase'), ('purchase_refund','Purchase Refund'), ('cash', 'Cash'), ('bank', 'Bank and Checks'), ('general', 'General'), ('situation', 'Opening/Closing Situation'), ('trust', 'Trust Fund')], 'Type', size=32, required=True,
                                 help="Select 'Sale' for customer invoices journals."\
                                 " Select 'Purchase' for supplier invoices journals."\
                                 " Select 'Cash' or 'Bank' for journals that are used in customer or supplier payments."\
                                 " Select 'General' for miscellaneous operations journals."\
				 " Select 'Trust Fund' for Client Trust Fund operations journal."\
                                 " Select 'Opening/Closing Situation' for entries generated for new fiscal years.")
	

class law_trust_account(models.Model):
	_name = 'law.trust.accounting'

	@api.multi
        def _get_period(self): return self.env['account.period'].find().id
	
	@api.one
	@api.depends('number')
	def _compute_transaction_name(self):
	    self.name = 'Transaction-' + str(self.number or 'Draft') + '-' + str(self.ref)


        @api.one
	@api.depends('write_date')
	def _compute_narration(self):
	    if self.operation == 'deposit':
	       self.narration = 'Deposit from ' + self.client_id.name + ' for ' +  ("'" + self.matter_id.name + "'" if self.matter_id else 'all matters')
	    elif self.operation == 'draw':
	       self.narration = 'Withdrawal for ' + self.client_id.name + ' for ' +  ("'" + self.matter_id.name + "'" if self.matter_id else 'all matters')
	    elif self.operation == 'transfer':
	       self.narration = 'Transfer from ' + "'" + self.matter_from.name + "' "  + 'to ' + "'" + self.matter_to.name + "'"
	    elif self.operation == 'trans-client': 
	       self.narration = 'Transfer from '  + self.client_id.name + ' to ' + "'" + self.matter_to.name + "'"
	    else:
	       self.narration = ''


	name = fields.Char('Transaction', compute='_compute_transaction_name', store=True)
	narration = fields.Char('Narration', compute='_compute_narration', store=True)
	transaction_date = fields.Date('Date', required=True, readonly=True, states={'draft':[('readonly',False)]})
	debit = fields.Float('Debit', required=True, readonly=True, states={'draft':[('readonly',False)]}, digits= dp.get_precision('Account'))
	credit = fields.Float('Credit', required=True, readonly=True, states={'draft':[('readonly',False)]}, digits= dp.get_precision('Account'))
	ref = fields.Char('Ref#', readonly=True, states={'draft':[('readonly',False)]}, required=True, help="Enter the source document reference e.g transaction slip or cheque number")
	description = fields.Text('Description', readonly=True, states={'draft':[('readonly',False)]})
	client_id = fields.Many2one('res.partner', string='Client', change_default=True, required=True, domain="[('customer', '=',True)]", readonly=True, states={'draft':[('readonly',False)]})
	client_trust = fields.Float('Trust Balance', related='client_id.trust_bal', digits= dp.get_precision('Account'))
	matter_id = fields.Many2one('law.matter', string='Matter', domain="[('client_id', '=',client_id)]",readonly=True, states={'draft':[('readonly',False)]})
	matter_trust = fields.Float('Matter Balance', related='matter_id.trust_bal', digits= dp.get_precision('Account'))
	journal_id = fields.Many2one('account.journal', 'Journal', required=True, domain="[('type', '=', 'trust')]",  readonly=True, states={'draft':[('readonly',False)]})
	state = fields.Selection([('draft','Draft'),('posted','Posted')], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
            help=' * The \'Draft\' status is used when a user is entering a new and unconfirmed transaction. \
                        \n* The \'Posted\' status is when the user has validated the transaction and entries have been created in respective ledger accounts')
	number = fields.Char('Number', readonly=True)
	move_id = fields.Many2one('account.move', 'Account Entry', copy=False)
	period_id = fields.Many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]})
	cr_account_id = fields.Many2one('account.account', 'Account to Credit',  readonly=True, states={'draft':[('readonly',False)]}, 
			help="This should be a Liability account for Client Funds held in Trust", domain="[('user_type.code', '=', 'liability')]")
	dr_account_id = fields.Many2one('account.account', 'Account to Debit',  readonly=True, states={'draft':[('readonly',False)]}, 
			help="This should be a Bank Account for Client Trust Fund", domain="[('type', '=', 'liquidity')]")
	#move_ids = fields.One2many('account.move.line', '', related='move', string='Journal Items', readonly=True)
	operation = fields.Selection([('deposit','Deposit'),('draw','Withdrawal'), ('transfer','Transfer (Matter to Matter)'), 
		    ('trans-client','Transfer (Client to Matter)')], 'Transaction Type', 
		    readonly=True, states={'draft':[('readonly',False)]}, track_visibility='onchange', copy=False, required=True,
            		help=' * The \'Deposit\' - Here you record all Trust Account deposits from your client. \
			\n* The \'Withdrawal\' - Here you record all you Trust Account withdrawals. \
                        \n* The \'Transfer\' - Here you record all you client trust fund transfers from one matter to another.')
	matter_from = fields.Many2one('law.matter', string='Matter From', domain="['&',('client_id', '=',client_id),\
			('id', '!=', matter_to)]",readonly=True, states={'draft':[('readonly',False)]})
	matter_to = fields.Many2one('law.matter', string='Matter To', domain="['&',('client_id', '=',client_id), \
			('id', '!=', matter_from)]",readonly=True, states={'draft':[('readonly',False)]})
	ttype = fields.Char('Dr-Cr', size=2, default='dr')
	counter_part = fields.Integer('Conterpart Transaction')
	_defaults = {'period_id': _get_period}

	@api.one
	@api.constrains('state')
        def check_withdrawal_limit(self):	    
	    if self.operation != 'deposit':
                if self.matter_trust < 0  or  self.client_trust < 0:
                   raise ValidationError('Amount to ' + ('withdraw' if self.operation =='draw' else 'transfer') + ' is more than the balance in the Trust account')
	    if self.debit == 0  and self.credit == 0:
		   raise ValidationError('Amount to transact is zero!')
	

	def validate_trust_transaction(self, cr, uid, ids, context=None):
	    operation = self.browse(cr, uid, ids, context=context).operation
	    if operation == 'deposit' or operation == 'draw':
               self.action_move_line_create(cr, uid, ids, context=context)
	    else:
		record = self.browse(cr, uid, ids, context=context)
		number = ''
		if record.journal_id.sequence_id:
                   if not record.journal_id.sequence_id.active:
                        raise except_orm(_('Configuration Error!'), _("The Sequence Number for selected Journal is no Active"))
                   c = dict(context)
                   c.update({'fiscalyear_id': record.period_id.fiscalyear_id.id})
                   number = self.pool.get('ir.sequence').next_by_id(cr, uid, record.journal_id.sequence_id.id, context=c)

		self.browse(cr, uid, ids, context=context).write({'state': 'posted', 'number': number or '/'})
		self.browse(cr, uid, self.browse(cr, uid, ids, context=context).counter_part, context=context).write({'state': 'posted', 'number': number or '/'})
            return True

	def action_move_line_create(self, cr, uid, ids, context=None):
            '''
            Confirm the transaction  given in ids and create the journal entries for each of them
            '''
            if context is None:
               context = {}
            move_pool = self.pool.get('account.move')
            move_line_pool = self.pool.get('account.move.line')
            for transaction in self.browse(cr, uid, ids, context=context):
            	local_context = dict(context, force_company=transaction.journal_id.company_id.id)
            	if transaction.move_id:
                	continue
		company_currency = transaction.journal_id.company_id.currency_id.id
		current_currency = company_currency
            	ctx = context.copy()
            	ctx.update({'date': transaction.transaction_date})
            	# Create the account move record.
		seq_obj = self.pool.get('ir.sequence')
		if transaction.number:
		   name = transaction.number
		elif transaction.journal_id.sequence_id:
		   if not transaction.journal_id.sequence_id.active:
			raise except_orm(_('Configuration Error!'), _("The Sequence Number for selected Journal is no Active"))
		   c = dict(context)
		   c.update({'fiscalyear_id': transaction.period_id.fiscalyear_id.id})
		   name = seq_obj.next_by_id(cr, uid, transaction.journal_id.sequence_id.id, context=c)
		else:
		   raise except_orm(_('Configuration Error!'), _("No defined sequence Number for the selected Journal ID"))
		if not transaction.ref:
		   ref = name.replace('/','')
		else:
		   ref = transaction.ref
		move = {
         	   'name': name,
         	   'journal_id': transaction.journal_id.id,
         	   'narration': transaction.description,
         	   'date': transaction.transaction_date,

         	   'ref': ref,
           	   'period_id': transaction.period_id.id,
     		}
		    
            	move_id = move_pool.create(cr, uid, move, context=context)
            	# Create the first move-line of the transaction
		#debit = credit = 0.0
		#debit = transaction.debit	
		sign = transaction.debit - transaction.credit < 0 and -1 or 1
		move_line = {
             	   	'name': name or '/',
               		'debit': transaction.credit,
                	'credit': transaction.debit,
                	'account_id': transaction.dr_account_id.id or transaction.journal_id.default_debit_account_id.id,
                	'move_id': move_id,
                	'journal_id': transaction.journal_id.id,
                	'period_id': transaction.period_id.id,
                	'partner_id': transaction.client_id.id,
                	'currency_id': company_currency <> current_currency and  current_currency or False,
                	'amount_currency': (sign * abs(transaction.debit) # amount < 0 for refunds
                    		if company_currency != current_currency else 0.0),
                	'date': transaction.transaction_date,
                	'date_maturity': transaction.transaction_date
           	}
            	move_line_pool.create(cr, uid, move_line, local_context)

                sign = transaction.debit - transaction.credit < 0 and -1 or 1
		move_line = {
                        'name': name or '/',
                        'debit': transaction.debit,
                        'credit': transaction.credit,
                        'account_id': transaction.cr_account_id.id or transaction.journal_id.default_credit_account_id.id,
                        'move_id': move_id,
                        'journal_id': transaction.journal_id.id,
                        'period_id': transaction.period_id.id,
                        'partner_id': transaction.client_id.id,
                        'currency_id': company_currency <> current_currency and  current_currency or False,
                        'amount_currency': (sign * abs(transaction.credit) # amount < 0 for refunds
                                if company_currency != current_currency else 0.0),
                        'date': transaction.transaction_date,
                        'date_maturity': transaction.transaction_date
                }
		move_line_pool.create(cr, uid, move_line, local_context)
            	# We post the transaction.
            	self.write(cr, uid, [transaction.id], {
                	'move_id': move_id,
                	'state': 'posted',
                	'number': name,
           	})
            	if transaction.journal_id.entry_posted:
                	move_pool.post(cr, uid, [move_id], context={})
        	return True
	@api.multi	
	def unlink(self):
	    for transaction in self:
		if transaction.state not in ('draft'):
	           raise except_orm(_('Invalid Action!'), _("Cannot delete trust accounting transaction entries which are already posted to the Journal!"))
	    return super(law_trust_account, self).unlink()

	@api.model
	def create(self, vals):
	    if vals.get('operation') == 'transfer':
		vals.update({'matter_id': vals.get('matter_from'), 'ttype': 'dr', 'credit': 0.00})
		debit = super(law_trust_account, self).create(vals)
		db = vals.get('debit')
		vals.update({'credit': db, 'debit': 0.00, 'matter_id': vals.get('matter_to'), 'counter_part': debit.id, 'ttype': 'cr'})	
	    	credit= super(law_trust_account, self).create(vals)
		debit.write({'counter_part': credit.id})
	    	return debit
	    elif vals.get('operation') == 'trans-client':
		vals.update({'ttype': 'dr', 'credit': 0.00})
                debit = super(law_trust_account, self).create(vals)
		db = vals.get('debit')
		vals.update({'credit': db, 'debit': 0.00, 'matter_id': vals.get('matter_to'), 'counter_part': debit.id, 'ttype': 'cr'})
                credit = super(law_trust_account, self).create(vals)
		debit.write({'counter_part': credit.id})
                return debit
	    elif vals.get('operation') == 'deposit':
		vals.update({'ttype': 'cr', 'debit': 0.00})
		return super(law_trust_account, self).create(vals)
	    else:## Its a Withdrawal
		vals.update({'ttype': 'dr', 'credit': 0.00})
		if vals.get('matter_id'):
		   trust = self.env['law.matter'].browse([vals.get('matter_id')]).trust_bal
		   if vals.get('debit') > self.matter_id.browse([vals.get('matter_id')]).trust_bal:
		      raise except_orm(_('Insufficient Funds!'), _("Amount to withdraw is more than the balance in the Trust account for this matter"))
		else:
		    if vals.get('debit') > self.client_id.browse([vals.get('client_id')]).trust_bal:
			raise except_orm(_('Insufficient Funds!'), _("Amount to withdraw is more than the balance in the Trust account for this client"))
		return super(law_trust_account, self).create(vals)

	@api.one
	def write(self,vals):
	    if vals.get('operation') == 'transfer':
		if self.operation == 'deposit':
		   vals.update({'ttype': 'cr', 'debit': 0.00, 'matter_id': vals.get('matter_to'),
                                'journal_id': vals.get('journal_id') or self.journal_id.id,
                                'transaction_date': vals.get('transaction_date') or self.transaction_date,
                                 'client_id': vals.get('client_id') or self.client_id.id,
                                 'ref': vals.get('ref') or self.ref
                                 })
		   super(law_trust_account, self).write(vals)
		   db = vals.get('credit') or self.credit
		   vals.update({'ttype': 'dr','debit': db, 'credit': 0.00, 'matter_id': vals.get('matter_from'),
                                 'counter_part': self.id,
                                 'journal_id': vals.get('journal_id') or self.journal_id.id,
                                 'transaction_date': vals.get('transaction_date') or self.transaction_date,
                                 'client_id': vals.get('client_id') or self.client_id.id,
                                 'ref': vals.get('ref') or self.ref

                                 })
		   debit = super(law_trust_account, self).create(vals)
                   self.write({'counter_part': debit.id})
                   return
		
	    elif vals.get('operation') == 'trans-client':
		if self.operation == 'deposit':
		    vals.update({'ttype': 'cr', 'debit': 0.00, 'matter_id': vals.get('matter_to'),
				'journal_id': vals.get('journal_id') or self.journal_id.id,
				'transaction_date': vals.get('transaction_date') or self.transaction_date,
                                 'client_id': vals.get('client_id') or self.client_id.id,
                                 'ref': vals.get('ref') or self.ref
				 })
		    super(law_trust_account, self).write(vals)
		    db = vals.get('credit') or self.credit
		    vals.update({'ttype': 'dr','debit': db, 'credit': 0.00, 'matter_id': None,
				 'counter_part': self.id, 
				 'journal_id': vals.get('journal_id') or self.journal_id.id,
				 'transaction_date': vals.get('transaction_date') or self.transaction_date,
				 'client_id': vals.get('client_id') or self.client_id.id,
				 'ref': vals.get('ref') or self.ref
				 
				 })
		    debit = super(law_trust_account, self).create(vals)
		    self.write({'counter_part': debit.id})
		    return
		elif self.operation == 'draw':
		    vals.update({'ttype': 'dr', 
				'credit': 0.00, 
				'matter_id': None ,
				'journal_id': vals.get('journal_id') or self.journal_id.id,
                                'transaction_date': vals.get('transaction_date') or self.transaction_date,
                                'client_id': vals.get('client_id') or self.client_id.id,
                                'ref': vals.get('ref') or self.ref
				})
		    super(law_trust_account, self).write(vals)
		    cr = vals.get('debit') or self.debit
		    vals.update({'ttype': 'cr','credit': cr,
				 'debit': 0.00, 
				 'matter_id': vals.get('matter_to'), 
				 'counter_part': self.id,
				 'journal_id': vals.get('journal_id') or self.journal_id.id,
                                 'transaction_date': vals.get('transaction_date') or self.transaction_date,
                                 'client_id': vals.get('client_id') or self.client_id.id,
                                 'ref': vals.get('ref') or self.ref
				 })
		    credit = super(law_trust_account, self).create(vals)
		    return self.write({'counter_part': credit.id})
		else: # it was a transfer
		   if self.ttype == 'dr':
		      vals.update({'ttype': 'dr', 'credit': 0.00, 'matter_id': None, 'matter_from': None })
		      super(law_trust_account, self).write(vals)
		      cr = vals.get('debit') or self.debit
		      vals.update({'ttype': 'cr','credit': cr, 'debit': 0.00, 'matter_id': vals.get('matter_to') or self.matter_to })
		      return self.browse([self.counter_part]).write(vals)

	    elif vals.get('operation') == 'deposit':
		if self.operation == 'transfer' or self.operation == 'trans-client':
		    self.browse([self.counter_part]).unlink()
		    vals.update({'ttype': 'cr', 'debit': 0.00, 'matter_from': None, 'matter_to': None, 'counter_part': None})
		    super(law_trust_account, self).write(vals)
		else: #it was a withdrawal
		    vals.update({'ttype': 'cr', 'debit': 0.00})
		    super(law_trust_account, self).write(vals)
	    elif vals.get('operation') == 'draw':
		if self.operation == 'transfer' or self.operation == 'trans-client':
		    self.browse([self.counter_part]).unlink()
                    vals.update({'ttype': 'dr', 'credit': 0.00, 'matter_from': None, 'matter_to': None, 'counter_part': None})
                    super(law_trust_account, self).write(vals)
		else: #it was a deposit
		    vals.update({'ttype': 'dr', 'credit': 0.00,})
                    super(law_trust_account, self).write(vals)

	    else:## The operation is not changing hence same logic as in def create
		if self.counter_part and self.ttype == 'dr': #debit transfer
		   if self.operation == 'transfer':
		      	vals.update({'matter_id': vals.get('matter_from') or self.matter_from.id})
                	super(law_trust_account, self).write(vals)
                	db = vals.get('debit') or self.debit
                	vals.update({'credit': db, 'debit': 0.00, 'matter_id': vals.get('matter_to') or self.matter_to.id})
			return super (law_trust_account, self.browse([self.counter_part])).write(vals)
		   if self.operation == 'trans-client':
                        super(law_trust_account, self).write(vals)
                        db = vals.get('debit') or self.debit
                        vals.update({'credit': db, 'debit': 0.00, 'matter_id': vals.get('matter_to') or self.matter_to.id})
			return super (law_trust_account, self.browse([self.counter_part])).write(vals)
		elif self.counter_part and self.ttype == 'cr': #credit transfer
		   if self.operation == 'transfer':
			vals.update({'matter_id': vals.get('matter_to') or self.matter_to.id})
			super(law_trust_account, self).write(vals)
			cr = vals.get('credit') or self.credit
			vals.update({'debit': cr, 'credit': 0.00, 'matter_id': vals.get('matter_from') or self.matter_from.id})
			return super (law_trust_account, self.browse([self.counter_part])).write(vals)
		   if self.operation == 'trans-client':
			vals.update({'matter_id': vals.get('matter_to') or self.matter_to.id})
			super(law_trust_account, self).write(vals)
			cr = vals.get('credit') or self.credit
			vals.update({'debit': cr, 'credit': 0.00, 'matter_id': None})
			return super (law_trust_account, self.browse([self.counter_part])).write(vals)
		
		else: #Not a transfer transaction; It is either withdrawal or deposit
		    return super(law_trust_account,self).write(vals)
		
		


class law_invoice(models.Model):
	_inherit = 'account.invoice'
	
	partner_id = fields.Many2one('res.partner', string='Client', change_default=True, required=True, readonly=True, states={'draft': [('readonly', False)]},
		track_visibility='always')
	matter_id = fields.Many2one('law.matter', string='Matter', required=True, readonly=True, states={'draft': [('readonly', False)]}, 
		track_visibility='always', domain="[('client_id', '=', partner_id)]")
	user_id = fields.Many2one('res.users', string='Prepared by', track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)]},
        	default=lambda self: self.env.user)

	
	@api.multi
	def prepare_bills(self, matter_id):
	  if matter_id:
	    values = {}
	    res = {'value':{'invoice_line':[]}}
	    for bill in self.env['law.matter'].browse([matter_id]).bill_ids:
		if bill.billable and bill.state =='unbilled':
		   values = {   'product_id':bill.id, 
				'price_unit': bill.sell_price, 
				'name': bill.name, 
			    	'quantity': 1.00, 
				'account_id': self.env['ir.property'].get('property_account_income_categ', 'product.category')
			    }
		   res['value']['invoice_line'].append(values)
	    if res['value']['invoice_line'] == []: 
	       raise except_orm(_('Warning!'), _('No billable legal fees for this client and the selected matter.\n Please ensure that you have generated some legal fees before billing the matter'))
	    return res

	@api.multi
    	def invoice_validate(self):
	    for bill in self.invoice_line:
		if  bill.product_id.state == 'unbilled': bill.product_id.write({'state': 'billed'})
		else: bill.unlink()
            return super(law_invoice, self).invoice_validate()
	
	@api.multi
    	def action_cancel(self):
	    res = super(law_invoice, self).action_cancel()
	    if res:
		for bill in self.invoice_line:
		    bill.product_id.write({'state': 'unbilled'})
	    return res

	@api.multi
    	def action_cancel_draft(self):
	    for inv in self:
		for bill in inv.invoice_line:
		    if bill.product_id.state =='billed':
			bill.unlink()
	    return super(law_invoice, self).action_cancel_draft()


class law_move_lines(models.Model):
	_inherit = 'account.move.line'

	product_id = fields.Many2one('law.bill', 'Legal Fees')

class law_voucher(models.Model):
	_inherit = 'account.voucher'


	@api.onchange('source')	
	def _get_payment_journal_id(self):
		if self.source == 'trust':
		    return {'domain':{'journal_id':[('type','in',['bank'])]}}
		else:
		   return {'domain':{'journal_id':[('type','in',['bank', 'cash'])]}}

	source = fields.Selection([('direct','Direct Payment (Cash/Cheque)'),('trust-matter','Trust Fund - Matter Balance'), ('trust-client','Trust Fund - Client Balance')], 'Payment Source', required=True, readonly=True, states={'draft':[('readonly',False)]})
	journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]})


	@api.one
	@api.constrains('source', 'journal_id', 'amount')
	def check_trust_cash(self):
	    if (self.source == 'trust-matter' or self.source == 'trust-client') and self.journal_id.type =='cash':
	    	raise ValidationError("For 'Trust Fund' as a 'Payment Source', do not select Cash as the 'Payment Option'")
	    elif self.amount == 0:
		raise ValidationError("Paid Amount is Zero!")

	def action_move_line_create(self, cr, uid, ids, context=None):
	   voucher = self.browse(cr, uid, ids, context=context)
	   if voucher.source =='trust-matter':#pay from matter operating balance
	    inv_obj = self.pool.get('account.invoice')
	    for vou in voucher.line_cr_ids:
		invoice = inv_obj.browse(cr, uid, inv_obj.search(cr, uid, [('move_id', '=', vou.move_line_id.move_id.id)], context=context), context=context)
		if invoice.matter_id.op_bal < vou.amount:
		   raise except_orm(_('Insufficient Funds!'), _('Invoice: ' + str(invoice.number)+ '\n\
					Matter: ' + str(invoice.matter_id.name)+'\n\
					Operating Balance: '+ str(invoice.matter_id.op_bal)+'\n\
					Allocated Amount: '+ str(vou.amount) ))
	        else:
		   invoice.matter_id.write({'op_used':invoice.matter_id.op_used + vou.amount})
	   if voucher.source =='trust-client':#pay from Client operating balance
            inv_obj = self.pool.get('account.invoice')
            for vou in voucher.line_cr_ids:
                invoice = inv_obj.browse(cr, uid, inv_obj.search(cr, uid, [('move_id', '=', vou.move_line_id.move_id.id)], context=context), context=context)
                if invoice.partner_id.op_bal < vou.amount:
                   raise except_orm(_('Insufficient Funds!'), _('Invoice: ' + str(invoice.number)+ '\n\
                                        Client: ' + str(invoice.partner_id.name)+'\n\
                                        Allocated Amount: '+ str(vou.amount)+'\n\
                                        Client Operating Balance: '+ str(invoice.partner_id.op_bal) ))
                else:
                   invoice.partner_id.write({'op_used':invoice.partner_id.op_used + vou.amount})

	   super(law_voucher, self).action_move_line_create(cr, uid, ids, context=context)
	   return True
	    

class law_invoice_lines(models.Model):
	_inherit = 'account.invoice.line'

	product_id = fields.Many2one('law.bill', string='Billable Item', ondelete="restrict", domain="[('client_id', '=', parent.partner_id)]", index=True)
	name = fields.Char('Description', required=True)
	
	@api.multi
	def bill_id_change(self, bill_id, qty=0, name='', partner_id=False):
	 values={}
	 if not partner_id:
	  raise except_orm(_('No Client Selected!'), _("You must first select the Client and the Matter to be billed!"))
	 bill = self.env['law.bill'].browse(bill_id)
	 values['price_unit'] = bill.sell_price
	 values['name'] = bill.name
	 #_logger.info('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXxx ...........................:%s' %expense_id)
         return {'value': values}
	 
class law_matter_trust_balances(models.Model):
	_inherit = 'law.matter'
	
	@api.one
	def _compute_matter_trust_bal(self):
		total_credit = 0.00 
		total_debit = 0.00
		for transaction in self.transactions.search([('state', '=' , 'posted'), ('matter_id', '=' , self.id)]):
			total_credit += transaction.credit
			total_debit += transaction.debit
		self.trust_bal = total_credit - total_debit

	@api.one
	@api.depends('op_used')
	def _compute_matter_operating_bal(self):
	    total_amount = 0.00
	    for op in self.transactions.search([('state', '=' , 'posted'), ('matter_id', '=' , self.id), ('operation', '=' , 'draw')]):
		total_amount += op.debit
	    self.op_bal = total_amount - self.op_used

	@api.one
	def compute_unpaid_fee(self):
	   unpaid = 0.0
	   for invoice in self.invoices.search([('state', '=' , 'open'), ('matter_id', '=' , self.id)]):
	       unpaid += invoice.residual
	   self.unpaid_fee = unpaid

	trust_bal = fields.Float('Trust Balance', compute='_compute_matter_trust_bal', digits= dp.get_precision('Account'))
	transactions = fields.One2many('law.trust.accounting', 'matter_id', string='Trust Account Transactions:')
	op_used = fields.Float('Amount used', digits= dp.get_precision('Account'))
	op_bal = fields.Float('Balance', compute='_compute_matter_operating_bal', digits= dp.get_precision('Account'))
	unpaid_fee = fields.Float('Unpaid Fees', compute='compute_unpaid_fee', digits= dp.get_precision('Account'))
	invoices = fields.One2many('account.invoice', 'matter_id', string='Invoices raised:')
	
	@api.one
	@api.constrains('op_used')
	def check_matter_op_balance(self):
	    if self.op_bal < 0:
		raise ValidationError('Insufficient Operating Balance for this matter!')
		 

class law_client_trust_balances(models.Model):	
	_inherit = 'res.partner'
	
        @api.one
        def _compute_client_trust_bal(self):
                total_credit = 0.00
                total_debit = 0.00
		for transaction in self.transactions.search([('state', '=' , 'posted'), ('matter_id', '=' , False), ('client_id', '=' , self.id)]):
			total_credit += transaction.credit
			total_debit += transaction.debit
		self.trust_bal = total_credit - total_debit
	
	@api.one
	def compute_unbilled_fee(self):
	    total = 0.00
	    for bill in self.bill_ids.search([('client_id', '=', self.id), ('billable', '=', True), ('state', '=', 'unbilled')]):
		total += bill.sell_price
	    self.unbilled_fee = total

        @api.one
        def compute_unpaid_fee(self):
            unpaid = 0.00
            for invoice in self.invoices.search([('partner_id', '=', self.id), ('state', '=', 'open')]):
                unpaid += invoice.residual
            self.unpaid_fee = unpaid

	@api.one
	@api.depends('op_used')
	def _compute_client_op_bal(self):
	    total =0.00
	    for withdrawal in self.transactions.search([('client_id', '=', self.id), ('operation', '=', 'draw'), ('state', '=', 'posted'), ('matter_id', '=', False)]):
		total += withdrawal.debit
	    self.op_bal = total - self.op_used

	@api.one
	def compute_events(self):
	    count = 0
	    for event in self.env['calendar.event'].search([]):
		for partner in event.partner_ids:
		    if partner.id == self.id:
			count +=1
	    self.events = count

	events = fields.Integer('Events/Meetings', compute='compute_events')
	comment = fields.Html('Internal Notes')
	trust_bal = fields.Float('Trust Balance', compute='_compute_client_trust_bal', digits= dp.get_precision('Account'))
	bill_ids = fields.One2many('law.bill', 'client_id', 'Time/Expenses:')
	unbilled_fee = fields.Float('Unbilled Fees', compute='compute_unbilled_fee', digits= dp.get_precision('Account'))
	unpaid_fee = fields.Float('Unpaid Fees', compute='compute_unpaid_fee', digits= dp.get_precision('Account'))
	op_bal = fields.Float('Operating Balance', compute='_compute_client_op_bal', digits= dp.get_precision('Account'))
	op_used = fields.Float('Operating Used', digits= dp.get_precision('Account'))
	transactions = fields.One2many('law.trust.accounting', 'client_id', string='Trust Account')
	invoices = fields.One2many('account.invoice', 'partner_id', string='Invoices Raised:')

        @api.one
        @api.constrains('op_used')
        def check_client_op_balance(self):
            if self.op_bal < 0:
                raise ValidationError('Insufficient Operating Balance for this client!')




