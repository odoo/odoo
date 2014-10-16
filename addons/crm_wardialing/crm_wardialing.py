# -*- coding: utf-8 -*-

from openerp import models, fields, api
import ari
import requests
from requests import HTTPError
import time
#----------------------------------------------------------
# Models
#----------------------------------------------------------

class crm_phonecall(models.Model):
	_inherit = "crm.phonecall"

	_order = "sequence, id"

	to_call = fields.Boolean("Call Center Call", default = False)
	made_call = fields.Boolean("Made Call", default = False)
	sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of Phonecalls.", default = 10)
	start_time = fields.Integer("Start time")

	@api.multi
	def call_partner(self):

		print("CALL FUNCTION")
		print(self)
		print(self.partner_id.phone)
		client = ari.connect('http://localhost:8088', 'asterisk', 'asterisk')

		incoming = client.channels.originate(endpoint="SIP/"+self.partner_id.phone, app="bridge-dial", appArgs="SIP/2002")
		self.start_time = int(time.time())
		
		def incoming_on_start(channel,event):
			print("ANSWERED")
		def on_start(incoming, event):
			"""Callback for StasisStart events.

			When an incoming channel starts, put it in the holding bridge and
			originate a channel to connect to it. When that channel answers, create a
			bridge and put both of them into it.

			:param incoming:
			:param event:
			"""
			print("ON_START ODOO")
		print("BEFORE BINDING")
		#Not workign don't know why
		incoming.on_event('StasisStart', incoming_on_start)
		client.on_channel_event('StasisStart', on_start)
		print("AFTER BINDING")
		return incoming.json
		
	@api.multi
	def hangup_partner(self, channel):
		client = ari.connect('http://localhost:8088', 'asterisk', 'asterisk')
		current_channels = client.channels.list()
		print(self.duration)
		
		if (len(current_channels) != 0):
		    for chan in current_channels:
		        if(chan.json.get('id') == channel.get('id')):
					stop_time = int(time.time())
					duration = float(stop_time - self.start_time)
					self.duration = float(duration/60.0)				
					chan.hangup()	
	
	@api.multi
	def get_information(self):
		return {"partner_name": self.partner_id.name,
				"partner_image_small": self.partner_id.image_small,
				"partner_email": self.partner_id.email,
				"partner_title": self.partner_id.title.name,
				"partner_phone": self.partner_id.phone,
				"partner_mobile": self.partner_id.mobile,
				"opportunity_name": self.opportunity_id.name,
				"opportunity_priority": self.opportunity_id.priority,
				"opportunity_planned_revenue": self.opportunity_id.planned_revenue,
				"opportunity_title_action": self.opportunity_id.title_action,
				"opportunity_company_currency": self.opportunity_id.company_currency.id,
				"opportunity_probability": self.opportunity_id.probability}

	@api.one
	def get_info(self):
		print("INFO ONE")
		print(self.opportunity_id.name)
		return {"id": self.id,
				"description": self.description,
				"partner_name": self.partner_id.name,
				"partner_image_small": self.partner_id.image_small,
				"partner_email": self.partner_id.email,
				"partner_title": self.partner_id.title.name,
				"partner_phone": self.partner_id.phone,
				"partner_mobile": self.partner_id.mobile,
				"opportunity_name": self.opportunity_id.name,
				"opportunity_id": self.opportunity_id.id,
				"opportunity_priority": self.opportunity_id.priority,
				"opportunity_planned_revenue": self.opportunity_id.planned_revenue,
				"opportunity_title_action": self.opportunity_id.title_action,
				"opportunity_company_currency": self.opportunity_id.company_currency.id,
				"opportunity_probability": self.opportunity_id.probability}

	@api.model
	def get_list(self, current_search):
		return {"phonecalls": self.search([('to_call','=',True)], order='sequence').get_info()}

class crm_lead(models.Model):
	_inherit = "crm.lead"

	@api.one
	def create_call_center_call(self):
		
		phonecall = self.env['crm.phonecall'].create({
				'name' : self.name
				});
		phonecall.to_call = True
		phonecall.opportunity_id = self.id
		phonecall.partner_id = self.partner_id
		phonecall.state = 'pending'

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
		return self._context.get('phonecall').get('opportunity_id')[1]

	description = fields.Text('Description', default = _default_description)
	opportunity_name = fields.Char(default = _default_phonecall, readonly=True)
	@api.multi
	def save(self):
		phonecall = self.env['crm.phonecall'].browse(self._context.get('phonecall').get('id'))
		phonecall.description = self.description
		print(phonecall.description)
		return {}

