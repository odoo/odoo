##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
#
# $Id$
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

from osv import fields,osv, orm
import time
import tools

class campaign_campaign(osv.osv):
	_name = "campaign.campaign"
	_columns = {
		'name': fields.char('Name', size=60, required=True),
		'info': fields.text('Description'),
		'costs': fields.float('Initial Costs'),
		'date_start': fields.date('Start Date'),
		'date_stop': fields.date('Stop Date'),
		'planned_costs': fields.float('Planned Costs'),
		'planned_revenue': fields.float('Planned Revenue'),
		'step_id': fields.one2many('campaign.step','campaign_id', 'Campaign Steps')
	}
campaign_campaign()

class campaign_steps(osv.osv):
	_name = "campaign.step"
	_columns = {
		'name': fields.char('Step Name', size=60, required=True),
#TODO: use sequence instead of priority
		'priority': fields.integer('Sequence', required=True),
		'info': fields.text('Description'),
		'procent': fields.float('Success Rate (0<x<1)'),
		'costs': fields.float('Step Costs'),
		'active': fields.boolean('Active'),
		'start_date': fields.date('Start Date'),
		'stop_date': fields.date('Stop Date'),
		'max_try': fields.integer('Max Attemps'),
		'campaign_id': fields.many2one('campaign.campaign', 'Campaign')
	}
	_defaults = {
		'active':lambda *a: 1,
		'max_try':lambda *a: 1
	}
	_order = 'priority'
campaign_steps()

class campaign_partner(osv.osv):
	_name = "campaign.partner"
	_columns = {
		'name': fields.char('Name / Reference', size=64, required=True),
		'user_id': fields.many2one('res.users', 'Salesman'),
		'step': fields.many2one('campaign.step', 'Step', required=True, states={'wait':[('readonly',True)],'stop':[('readonly',True)]}),
		'priority': fields.selection([('0','Very Low'),('1','Low'),('2','Medium'),('3','High'),('4','Very High')], 'Priority', required=True, states={'wait':[('readonly',True)],'stop':[('readonly',True)]}),
		'partner_id': fields.many2one('res.partner', 'Partner', required=True),
		'part_adr_id': fields.many2one('res.partner.address', 'Partner Address', required=True),
		'contact': fields.char('Partner Contact', size=64),
		'notes': fields.text('Prospect Notes'),

		'date_recall': fields.datetime('Call again on', states={'wait':[('readonly',True)],'stop':[('readonly',True)]}),
		'info': fields.text('Comments', states={'wait':[('readonly',True)],'stop':[('readonly',True)]}),
		'active': fields.boolean('Active'),
		'history_ids': fields.one2many('campaign.partner.history', 'camp_partner_id', 'History'),
		'campaign_id': fields.many2one('campaign.campaign', 'Campaign'),
		'state': fields.selection([('draft','Normal'), ('wait','Waiting'), ('stop','Stopped')], 'State', readonly=True)
	}
	_defaults = {
		'state': lambda *a: 'draft',
		'active': lambda *a: 1
	}
	_order = 'state,priority desc,name'

	def recall(self,cr, uid, ids, *args):
		res = self.read(cr,uid,ids,['date_recall', 'name', 'info', 'step'])
		for r in res:
			if not r['date_recall']:
				raise orm.except_orm('ValidateError', ('Error, choose a date', 'date_recall'))

		for r in res:
			self.pool.get('campaign.partner.history').create(cr, uid, {
				'name': 'Recall Later ' + str(r['date_recall']),
				'info': r['info'],
				'date': time.strftime('%Y-%m-%d %H:%M:%S'),
				'step_id': r['step'][0],
				'camp_partner_id': r['id']
			})
			self.pool.get('ir.cron').create(cr, uid, {
				'user_id': uid,
				'name': 'Campaign: Recall',
				'nextcall': r['date_recall'],
				'active': True,
				'numbercall': 1,
				'model': self._name,
				'function': 'write',
				'args': repr([[r['id']], {'date_recall':False, 'state':'draft'}])
			})
		self.write(cr, uid, ids, {'state':'wait'})
		return True

	def stop_camp(self,cr, uid, ids, *args):
		self.write(cr, uid, ids, {'state':'stop', 'active':0})
		return True

	def continue_camp(self, cr, uid, ids, *args):
		res = self.read(cr, uid, ids, ['info', 'state', 'step', 'campaign_id'])
		for r in res:
			self.pool.get('campaign.partner.history').create(cr, uid, {
				'name': r['step'][1],
				'info': r['info'],
				'date': time.strftime('%Y-%m-%d %H:%M:%S'),
				'step_id': r['step'][0],
				'camp_partner_id': r['id']
			})
			cr.execute('select id,start_date from campaign_step where priority>(select priority from campaign_step where id=%d) and campaign_id=%d order by priority limit 1', (r['step'][0],r['campaign_id'][0]))
			nextstep = cr.fetchone()
			if nextstep:
				dt = False
				if nextstep[1] > time.strftime('%Y-%m-%d'):
					dt = nextstep[1]
				self.write(cr, uid, [r['id']], {
					'step': nextstep[0],
					'state': 'draft',
					'info': '',
					'date_recall': dt,
					'active': True
				})
				if dt:
					self.recall(cr, uid, [r['id']])
		return True
campaign_partner()

class campaign_partner_history(osv.osv):
	_name = "campaign.partner.history"
	_columns = {
		'name': fields.char('History', size=64, required=True),
		'info': fields.text('Comments'),
		'date': fields.datetime('Date', readonly=True),
		'step_attempt': fields.integer('Attempt', readonly=True),
		'step_id': fields.many2one('campaign.step', 'Step', readonly=True),
		'camp_partner_id': fields.many2one('campaign.partner', 'Prospect', readonly=True),
	}
campaign_partner_history()

