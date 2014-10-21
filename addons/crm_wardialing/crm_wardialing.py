# -*- coding: utf-8 -*-

from openerp import models, fields, api
import ari
import requests
from requests import HTTPError
import time
from openerp.osv import osv, expression
from openerp.tools.translate import _
#----------------------------------------------------------
# Models
#----------------------------------------------------------


class crm_phonecall(models.Model):
	_inherit = "crm.phonecall"

	_order = "sequence, id"

	to_call = fields.Boolean("Call Center Call", default = False)
	made_call = fields.Boolean("Made Call", default = False)
	sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of Phonecalls.")
	start_time = fields.Integer("Start time")

	@api.multi
	def call_partner(self):

		print("CALL FUNCTION")
		print(self)
		try:
			client = ari.connect(self.env['ir.values'].get_default('sale.config.settings', 'asterisk_url'), 
				self.env['ir.values'].get_default('sale.config.settings', 'asterisk_login'), 
				self.env['ir.values'].get_default('sale.config.settings', 'asterisk_password'))
		except:
			raise osv.except_osv(_('Error!'), _('The connection to the Asterisk server failed. Please check your configuration.'))
		try:
			incoming = client.channels.originate(endpoint="SIP/"+self.opportunity_id.partner_id.phone, app="bridge-dial", 
				appArgs="SIP/"+self.env['ir.values'].get_default('sale.config.settings', 'asterisk_phone'))
			self.start_time = int(time.time())
			
			def incoming_on_start(channel,event):
				print("ANSWERED")
			def on_start(incoming, event):
				print("ON_START ODOO")
				
			print("BEFORE BINDING")
			#Not workign don't know why
			incoming.on_event('StasisStart', incoming_on_start)
			client.on_channel_event('StasisStart', on_start)
			print("AFTER BINDING")
			return incoming.json
		except:
			raise osv.except_osv(_('Error!'), _('You try to call a wrong phone number or the phonecall has been deleted. Please refresh the panel and check the phone number.'))
			

	@api.multi
	def hangup_partner(self, channel):
		try:
			client = ari.connect(self.env['ir.values'].get_default('sale.config.settings', 'asterisk_url'), 
				self.env['ir.values'].get_default('sale.config.settings', 'asterisk_login'), 
				self.env['ir.values'].get_default('sale.config.settings', 'asterisk_password'))
		except:
			raise osv.except_osv(_('Error!'), _('The connection to the Asterisk server failed. Please check your configuration.'))
		current_channels = client.channels.list()
		
		if (len(current_channels) != 0):
		    for chan in current_channels:
		        if(chan.json.get('id') == channel.get('id')):
					stop_time = int(time.time())
					duration = float(stop_time - self.start_time)
					self.duration = float(duration/60.0)	
					self.state = "done"
					self.to_call = False			
					chan.hangup()	

	@api.one
	def get_info(self):
		return {"id": self.id,
				"description": self.description,
				"partner_id": self.opportunity_id.partner_id.id,
				"partner_name": self.opportunity_id.partner_id.name,
				"partner_image_small": self.opportunity_id.partner_id.image_small,
				"partner_email": self.opportunity_id.partner_id.email,
				"partner_title": self.opportunity_id.partner_id.title.name,
				"partner_phone": self.opportunity_id.partner_id.phone,
				"partner_mobile": self.opportunity_id.partner_id.mobile,
				"opportunity_name": self.opportunity_id.name,
				"opportunity_id": self.opportunity_id.id,
				"opportunity_priority": self.opportunity_id.priority,
				"opportunity_planned_revenue": self.opportunity_id.planned_revenue,
				"opportunity_title_action": self.opportunity_id.title_action,
				"opportunity_company_currency": self.opportunity_id.company_currency.id,
				"opportunity_probability": self.opportunity_id.probability,
				"max_priority": self.opportunity_id._all_columns.get('priority').column.selection[-1][0]}

	@api.model
	def get_list(self, current_search):
		return {"phonecalls": self.search([('to_call','=',True)], order='sequence, id').get_info()}

class crm_lead(models.Model):
	_inherit = "crm.lead"
	in_call_center_queue = fields.Boolean("Is in the Call Center Queue", compute='compute_is_call_center')

	@api.one
	def compute_is_call_center(self):
		phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id),('to_call','=',True)])
		if phonecall:
			self.in_call_center_queue = True
		else:
			self.in_call_center_queue = False	

	@api.one
	def create_call_center_call(self):
		phonecall = self.env['crm.phonecall'].create({
				'name' : self.name
		});
		phonecall.to_call = True
		phonecall.opportunity_id = self.id
		phonecall.partner_id = self.partner_id
		phonecall.state = 'pending'

	@api.one
	def delete_call_center_call(self):
		phonecall = self.env['crm.phonecall'].search([('opportunity_id','=',self.id)])
		phonecall.unlink()

class crm_phonecall_log_wizard(models.TransientModel):
	_name = 'crm.phonecall.log.wizard';

	@api.multi
	def _default_description(self):
		if(self._context.get('phonecall').get('description') == "There is no description"):
			return ""
		else:
			return self._context.get('phonecall').get('description')		
	
	@api.multi
	def _default_phonecall(self):
		return self._context.get('phonecall').get('opportunity_name')

	description = fields.Text('Description', default = _default_description)
	opportunity_name = fields.Char(default = _default_phonecall, readonly=True)

	@api.multi
	def save(self):
		phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall').get('id'))
		phonecall.description = self.description
		return {
			'type': 'ir.actions.client',
			'tag': 'reload_panel',
		}
