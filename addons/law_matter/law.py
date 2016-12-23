# -*- coding: utf-8 -*-
from __future__ import division
from openerp import models, fields, api
from datetime import date, datetime, timedelta
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp

class law_activity_type(models.Model):
        _name = 'law.activity_type'
	_description = "Activity Type"
        _inherit = ["mail.thread"]
        _order = "id desc"

        name = fields.Char('Name of Activity', required=True)
        code = fields.Char(size=4)
	taxable = fields.Boolean('Taxable?', default=True)

class law_bill(models.Model):
        _name = 'law.bill'
	_description = "Time/Expense"
	_inherit = ["mail.thread"]
	_order = "id desc"

        def _expense_default_date(self):
         return datetime.now()

	@api.one
	@api.depends('travel_hours', 'labour_hours' )
	def _compute_total_hours(self):
	 self.total_hours = self.travel_hours + self.labour_hours

        @api.one
        @api.depends('start_date', 'end_date' )
        def _compute_labour_hours(self):
	 diff = datetime.strptime(self.end_date, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(self.start_date, DEFAULT_SERVER_DATETIME_FORMAT)
	 self.labour_hours = (diff.days * 24) + (diff.seconds / 3600)
	 if self.labour_hours < 0:
                raise ValidationError("'End Date' is older than 'Start Date' in time entry. Please correct this")
	
	@api.one
        @api.depends('activity_id', 'matter_id' )
	def _compute_bill_name(self):
	 if self.bill_type == 'activity':
	  self.name = self.matter_id.matter_id + "-" + self.activity_id.name
	 else:
	  self.name = self.matter_id.matter_id + "-" + self.expense_id.name

        @api.one
        @api.depends('cost_price', 'markup', 'lawyer_rate', 'flat_fee', 'total_hours', 'travel_hours','override_rate', 'override_hours', 'ride_rate', 'ride_hours')
        def _compute_expense_sell_price(self):
	    if self.bill_type == 'expense':
               self.sell_price = (1 + (self.markup /100)) * self.cost_price
	    if self.bill_type == 'activity' and self.billing_method == 'hour':
		if self.ride_rate == True and self.ride_hours == True:
		   self.sell_price = self.override_rate * self.override_hours
		elif self.ride_rate == True and self.ride_hours == False:
		   self.sell_price = self.override_rate * self.total_hours
		elif self.ride_rate == False and self.ride_hours == True:
		   	self.sell_price = self.lawyer_rate.rate * self.override_hours
		else:
		     self.sell_price = self.lawyer_rate.rate * self.total_hours
	    if self.bill_type == 'activity' and self.billing_method == 'flat':	
		self.sell_price = self.flat_fee
		


        def _expense_default_date(self):
         return datetime.now()

        name = fields.Char('Name', compute='_compute_bill_name', store=True)
	lawyer_id = fields.Many2one('res.users', 'Lawyer', domain="[('active', '=', True)]", required=True, readonly=True, states={'unbilled':[('readonly',False)]})
        client_id = fields.Many2one('res.partner', 'Client', domain="[('customer', '=', True)]", required=True, readonly=True, states={'unbilled':[('readonly',False)]})
        matter_id = fields.Many2one('law.matter', 'Matter', domain="[('client_id', '=', client_id)]", required=True, readonly=True, states={'unbilled':[('readonly',False)]})
	start_date = fields.Datetime('Start Date', default=_expense_default_date, readonly=True, states={'unbilled':[('readonly',False)]})
	end_date = fields.Datetime('End Date', default=_expense_default_date, readonly=True, states={'unbilled':[('readonly',False)]})
	billable = fields.Boolean('Billable?', default=True, readonly=True, states={'unbilled':[('readonly',False)]})
	state = fields.Selection([('unbilled','Not Billed'),('billed','Billed')], 'Status', readonly=True, track_visibility='onchange', copy=False, default='unbilled',
            help=' * The \'Not billed\' status is when the Time or Expense recorded has not been invoiced. \
                        \n* The \'billed\' status is when the Time or Expense recorded has  been invoiced and therefore cannot be altered')
	activity_id = fields.Many2one('law.activity_type', 'Activity', readonly=True, states={'unbilled':[('readonly',False)]})
	billing_method = fields.Selection([('hour','Hourly'),('flat','Flat Fee')], string='Billing Method', readonly=True, states={'unbilled':[('readonly',False)]})
	description = fields.Html(readonly=True, states={'unbilled':[('readonly',False)]})
	labour_hours = fields.Float('Labour Time(Hrs)', compute='_compute_labour_hours', digits=(32,2), store=True)
	travel_hours = fields.Float('Travel Time(Hrs)', readonly=True, states={'unbilled':[('readonly',False)]}, digits=(32,2))
	total_hours = fields.Float('Total Time(Hrs)', compute='_compute_total_hours', digits=(32,2), store=True)
	ride_hours = fields.Boolean('Override Time?', default=False, readonly=True, states={'unbilled':[('readonly',False)]}, digits=(32,2))
	ride_rate = fields.Boolean('Override Rate?', default=False, readonly=True, states={'unbilled':[('readonly',False)]}, digits= dp.get_precision('Account'))
	override_hours = fields.Float('Override Hrs', help="You can choose to override the actual billable hours to be used to bill the customer", readonly=True, states={'unbilled':[('readonly',False)]}, digits=(32,2))
	override_rate = fields.Float('Override Rate', help="You can choose to override the Lawyer hourly rate by specifying a different rate here", readonly=True, states={'unbilled':[('readonly',False)]}, digits=(32,2))
	lawyer_rate = fields.Many2one('law.lawyer_rate', 'Lawyer Rate', domain="[('lawyer', '=', lawyer_id )]", readonly=True, states={'unbilled':[('readonly',False)]}, digits=dp.get_precision('Account'))
	flat_fee = fields.Float('Flat Fee', readonly=True, states={'unbilled':[('readonly',False)]}, digits=dp.get_precision('Account'))
	bill_type = fields.Selection([('activity','Time'),('expense','Expense')], string='Time or Expense?', required=True, readonly=True, states={'unbilled':[('readonly',False)]})
	expense_id = fields.Many2one('law.expense_type', 'Expense', readonly=True, states={'unbilled':[('readonly',False)]})
	cost_price = fields.Float('Cost Price', readonly=True, states={'unbilled':[('readonly',False)]}, digits=dp.get_precision('Account'))
	markup = fields.Float('Markup(%)', readonly=True, states={'unbilled':[('readonly',False)]}, digits=(32,2))
	sell_price = fields.Float('Total Amount', compute='_compute_expense_sell_price', digits=dp.get_precision('Account'), store=True)
	expense_date = fields.Datetime('Expense Date', default=_expense_default_date, readonly=True, states={'unbilled':[('readonly',False)]})
	desc_exp = fields.Char('Description', readonly=True, states={'unbilled':[('readonly',False)]})

	@api.multi
	def unlink(self):
	    for bill in self:
	       if bill.id == bill.matter_id.one_fee:
		  bill.matter_id.one_fee = None
	    return super(law_bill, self).unlink()

	@api.one
	@api.constrains('travel_hours', 'end_date', 'start_date', 'override_rate', 'override_hours', 'flat_fee')
	def check_labour_time(self): # No Negative values
	    if self.travel_hours < 0 and self.bill_type == 'activity':
		raise ValidationError("Invalid 'Travel Time' entry, no negative values for time!")
	    if self.override_rate < 0 and self.billing_method == 'hour':
		 raise ValidationError("Invalid 'Override Rate' entry, no negative values for rate!")
	    if self.override_hours < 0 and self.billing_method == 'hour':
		raise ValidationError("Invalid 'Override Hours' entry, no negative values for time!")
	    if self.flat_fee < 0 and self.billing_method == 'flat':
		raise ValidationError("Invalid entry for 'Flat Fee', no negative values for fee!")
            diff = datetime.strptime(self.end_date, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(self.start_date, DEFAULT_SERVER_DATETIME_FORMAT)
            hours = (diff.days * 24) + (diff.seconds / 3600)
            if hours < 0:
               raise ValidationError("'End Date' is older than 'Start Date' in time entry. Please correct this")

	        

class law_expense_type(models.Model):
        _name = 'law.expense_type'
	_description = "Expense Type"
        _inherit = ["mail.thread"]
        _order = "id desc"

        name = fields.Char('Name of Expense', required=True)
        code = fields.Char(size=4)
	taxable = fields.Boolean('Taxable?', default=True)


class law_type(models.Model):
	_description = "Type of Law"
        _inherit = ["mail.thread"]
        _order = "id desc"
        _name = 'law.type'
	name = fields.Char('Category of Law', required=True)
	code = fields.Char(size=4)

class law_lawyer_rate(models.Model):
        _name = 'law.lawyer_rate'
	_description = "Lawyer Rate"
        _inherit = ["mail.thread"]
        _order = "id desc"

	@api.one
	@api.depends('write_date')
	def compute_name(self):
	    self.name = str(self.id).zfill(4) + '-' + str(self.lawyer.partner_id.name) + ' (' + str(self.code) + ')'

        name = fields.Char(compute='compute_name', store=True)
	code = fields.Char('Short Code', size=30, required=True)
	lawyer = fields.Many2one('res.users', 'Lawyer', required=True)
        rate = fields.Float('Hourly Rate', required=True, digits=dp.get_precision('Account'))

class law_calendar_events(models.Model):
	_inherit = ["calendar.event"]
	
	#checking = fields.Boolean('chech')
	matter_ids = fields.Many2many('law.matter', 'calendar_event_law_matter_rel', string='Matters', states={'done': [('readonly', True)]})

class law_matter(models.Model):
	_name = 'law.matter'
	_description = "Matter"
	_inherit = ['mail.thread']
	_order = "matter_id desc"

 	@api.one
	@api.depends('write_date')
        def _compute_matter_id(self):
	 self.matter_id = str(self.id).zfill(5)
	
	@api.one		
	def _compute_matter_age(self):
	 date_from = datetime.strptime(self.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
	 date_now = datetime.now()
	 self.matter_age = str((date_now - date_from).days) + ' Days'
	
	@api.one
	def compute_unbilled_fee(self):
	    total = 0.00
	    for bill in self.bill_ids.search([('matter_id', '=', self.id),('billable', '=', True), ('state', '=', 'unbilled')]):
		total += bill.sell_price
	    self.unbilled_fee = total

	@api.one
	def _compute_events(self):
	    count = 0
	    for record in self:
	        for event in record.env['calendar.event'].search([]):
		   for matter in event.matter_ids:
		       if matter.id == self.id:
		          count +=1
	    self.events = count


	name = fields.Char(required=True, readonly=True, states={'open':[('readonly',False)]})
	client_id = fields.Many2one('res.partner', 'Client', domain="[('customer', '=', True)]", required=True, readonly=True, states={'open':[('readonly',False)]})
	state = fields.Selection([('open','Open'),('closed','Closed')], string='Status', default='open', readonly=True, states={'open':[('readonly',False)]})
	assign_to = fields.Many2one('res.users', 'Lawyer Assigned', domain="[('active', '=', True)]", required=True, readonly=True, states={'open':[('readonly',False)]})
	law_type = fields.Many2one('law.type', 'Type of Law', required=True, readonly=True, states={'open':[('readonly',False)]})
	bill_method = fields.Selection([('hour','Hourly'),('contingency','Contingency'), ('flat_one','Flat Fee - One Time'), 
		('flat_recurr','Flat Fee - Recurring')], string='Billing Method', required=True, readonly=True, states={'open':[('readonly',False)]})
	description = fields.Html(readonly=True, states={'open':[('readonly',False)]})
	matter_id = fields.Char('Matter ID', compute='_compute_matter_id', store=True)
	matter_age = fields.Char('Matter Age', compute='_compute_matter_age')
	bill_ids = fields.One2many('law.bill', 'matter_id', string="Activities", readonly=True, states={'open':[('readonly',False)]})
	conti = fields.Float('Contingency Rate(%)', readonly=True, states={'open':[('readonly',False)]}, digits=dp.get_precision('Account'))
	flat_fee = fields.Float('Flat Fee', readonly=True, states={'open':[('readonly',False)]}, digits=dp.get_precision('Account'))
	one_fee = fields.Integer('One Time Fee', readonly=True, states={'open':[('readonly',False)]})
	unbilled_fee = fields.Float('Unbilled Fees', compute='compute_unbilled_fee', digits=dp.get_precision('Account'))
	events = fields.Integer('Events/Meetings', compute='_compute_events')

	@api.model
	def create(self, vals):
	    matter = super(law_matter, self).create(vals)
	    if vals.get('bill_method') == 'flat_one':
	       #matter = super(law_matter, self).create(vals)
	       # Create the One time fee  for this matter
	       values ={
	       	'client_id': matter.client_id.id,
		'matter_id': matter.id,
		'bill_type': 'activity',
		'lawyer_id': matter.assign_to.id,
		'billing_method': 'flat',
		'activity_id': 6,
		'flat_fee': matter.flat_fee,
		'billable': True
	       }
	       fee = self.env['law.bill'].create(values)
	       matter.write({'one_fee': fee.id})
	       #raise except_orm(_('Configuration Error!'), _(vals.get('bill_method')))
	    return matter

	@api.multi
	def write(self, vals):
	    if vals.get('bill_method') or vals.get('flat_fee'):
	       if vals.get('bill_method') == 'flat_one':
		  if self.one_fee != 0:
	          	for bill in self.bill_ids:
		    	    if bill.id == self.one_fee:
				bill.write({'billable': True, 'flat_fee': vals.get('flat_fee') or self.flat_fee})
		  	    else: bill.write({'billable': False})
		  else:
	 	      # Create the One time fee  for this matter
               	      values ={
                       	'client_id': self.client_id.id,
                       	'matter_id': self.id,
                	'bill_type': 'activity',
                	'lawyer_id': self.assign_to.id,
                	'billing_method': 'flat',
                	'activity_id': 6,
               		'flat_fee': vals.get('flat_fee'),
                	'billable': True
               	      }    
	   	      fee = self.env['law.bill'].create(values)
		      self.write({'one_fee': fee.id})
		      for bill in self.bill_ids:
                            if bill.id == self.one_fee:
                                bill.write({'billable': True})
                            else: bill.write({'billable': False})
	       elif vals.get('flat_fee'):
		    for bill in self.bill_ids:
			if bill.id == self.one_fee:
			   bill.write({'billable': True, 'flat_fee': vals.get('flat_fee')})
			   continue
		     
	       else: 
		 for bill in self.bill_ids:
		     bill.write({'billable': True})
	    return super(law_matter, self).write(vals)

	@api.multi
	def close_matter(self):
	    #raise except_orm(_('Invalid Action!'), _(self))
	    if self.bill_ids:
	       for bill in self.bill_ids:
		   if bill.state == 'unbilled':
		      raise except_orm(_('Invalid Action!'), _('You cannot close this matter which has legal fees due from client'))
	       self.write({'state': 'closed'})
	       return True
	    else: 
		self.write({'state': 'closed'})
		return True

	@api.multi
	def reopen_matter(self):
	    if self.state == 'closed':
		self.write({'state': 'open'})
		return True


	

