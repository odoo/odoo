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
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import fields, osv

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}

class marketing_campaign(osv.osv): #{{{
    _name = "marketing.campaign"
    _description = "Marketing Campaign"
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'object_id': fields.many2one('ir.model', 'Objects'),
        'mode':fields.selection([('test', 'Test'),
                                ('test_realtime', 'Realtime Time'),
                                ('manual', 'Manual'),
                                ('active', 'Active')],
                                 'Mode'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('running', 'Running'),
                                   ('done', 'Done'),
                                   ('cancelled', 'Cancelled'),],
                                   'State',), 
        'activity_ids': fields.one2many('marketing.campaign.activity', 
                                       'campaign_id', 'Activities'),
        'fixed_cost': fields.float('Fixed Cost'),                                       
        
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
    }
    
    def state_running_set(self, cr, uid, ids, *args):
        campaign = self.browse(cr, uid, ids[0])
        if not campaign.activity_ids :
            raise osv.except_osv("Error", "There is no associate activitity for the campaign")
        act_ids = [ act_id.id for act_id in campaign.activity_ids]
        act_ids  = self.pool.get('marketing.campaign.activity').search(cr, uid,
                                [('id', 'in', act_ids), ('start', '=', True)])
        if not act_ids :
            raise osv.except_osv("Error", "There is no associate activitity for the campaign")
        segment_ids = self.pool.get('marketing.campaign.segment').search(cr, uid,
                                            [('campaign_id', '=', campaign.id),
                                            ('state', '=', 'draft')])
        if not segment_ids :
            raise osv.except_osv("Error", "There is no associate semgnet for the campaign")
        self.write(cr, uid, ids, {'state': 'running'})
        return True
        
    def state_done_set(self, cr, uid, ids, *args):
        segment_ids = self.pool.get('marketing.campaign.segment').search(cr, uid,
                                            [('campaign_id', 'in', ids),
                                            ('state', '=', 'running')])
        if segment_ids :
            raise osv.except_osv("Error", "Camapign cannot be done before all segments are done")            
        self.write(cr, uid, ids, {'state': 'done'})
        return True
        
    def state_cancel_set(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'cancelled'})
        return True
marketing_campaign()#}}}

class marketing_campaign_segment(osv.osv): #{{{
    _name = "marketing.campaign.segment"
    _description = "Campaign Segment"

    _columns = {
        'name': fields.char('Name', size=64,required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign', 
                                                required=True),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object'),
        'ir_filter_id': fields.many2one('ir.filters', 'Filter'),
        'sync_last_date': fields.datetime('Date'),
        'sync_mode': fields.selection([('create_date', 'Create'),
                                      ('write_date', 'Write')],
                                      'Mode'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('running', 'Running'),
                                   ('done', 'Done'),
                                   ('cancelled', 'Cancelled')],
                                   'State',), 
        'date_run': fields.datetime('Running'),
        'date_done': fields.datetime('Done'),
    }
    
    _defaults = {
        'state': lambda *a: 'draft',
        'sync_mode': lambda *a: 'create_date',
    }
    
    def state_running_set(self, cr, uid, ids, *args):
        segment = self.browse(cr, uid, ids[0])
        if not segment.date_run:
            raise osv.except_osv("Error", "Segment cant be start before giving running date")
        if segment.campaign_id.state != 'running' :
            raise osv.except_osv("Error", "You have to start campaign first")
        self.write(cr, uid, ids, {'state': 'running'})
        return True
        
    def state_done_set(self, cr, uid, ids, *args):
        date_done = self.browse(cr, uid, ids[0]).date_done 
        if (date_done > time.strftime('%Y-%m-%d')):
            raise osv.except_osv("Error", "Segment cannot be closed before end date")

        wi_ids = self.pool.get("marketing.campaign.workitem").search(cr, uid,
                                [('state', 'in', ['inprogress', 'todo']),
                                 ('segment_id', '=', ids[0])])
        if wi_ids :
            raise osv.except_osv("Error", "Segment cannot be done before all workitems are processed")            
        self.write(cr, uid, ids, {'state': 'done'})
        return True
        
    def state_cancel_set(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'cancelled'})
        return True
        
    def process_segment(self, cr, uid, context={}):
        segment_ids = self.search(cr, uid, [('state', '=', 'running')])
        action_date = time.strftime('%Y-%m-%d %H:%M:%S')
        last_action_date = (datetime.now() + _intervalTypes['days'](-1) \
                                            ).strftime('%Y-%m-%d %H:%M:%S')
        for segment in self.browse(cr, uid, segment_ids):
            act_ids = self.pool.get('marketing.campaign.activity').search(cr, 
                                  uid, [('start', '=', True),
                                  ('campaign_id', '=', segment.campaign_id.id)])
            if (segment.sync_last_date and \
                segment.sync_last_date <= action_date )\
                 or not segment.sync_last_date :
                model_obj = self.pool.get(segment.object_id.model)
                object_ids = model_obj.search(cr, uid, [
                                        (segment.sync_mode, '<=', action_date),
                                (segment.sync_mode, '>=', last_action_date)])
                for o_ids in  model_obj.read(cr, uid, object_ids) :
                    partner_id = 'partner_id' in o_ids and o_ids['partner_id'] \
                                        or False
                    for act_id in act_ids:
                        wi_vals = {'segment_id': segment.id,
                                   'activity_id': act_id,
                                   'date': action_date,
                                   'partner_id': 1,
                                   'state': 'todo',
                                    }
                        print self.pool.get('marketing.campaign.workitem').create(cr,
                                                             uid, wi_vals)
                 
                self.write(cr, uid, segment.id, {'sync_last_date':action_date}) 
        return True

marketing_campaign_segment()#}}}

class marketing_campaign_activity(osv.osv): #{{{
    _name = "marketing.campaign.activity"
    _description = "Campaign Activity"

    _columns = {
        'name': fields.char('Name', size=64),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign'),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object'),
        'start': fields.boolean('Start'),
        'condition': fields.text('Condition'),
        'type': fields.selection([('email', 'E-mail'),
                                  ('paper', 'Paper'),
                                  ('action', 'Action'),
                                  ('subcampaign', 'Sub-Campaign')],
                                   'Type'),
        'email_template_id': fields.many2one('poweremail.templates','Email Template'),
        'report_id': fields.many2one('ir.actions.report.xml', 'Reports'),         
        'report_directory_id': fields.many2one('document.directory', 'Directory'),
        'server_action_id': fields.many2one('ir.actions.server', string='Action'),
        'to_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_to_id',
                                            'Next Activities'),
        'from_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_from_id',
                                            'Previous Activities'), 
        'subcampaign_id': fields.many2one('marketing.campaign', 'Sub-Campaign'),
        'subcampaign_segment_id': fields.many2one('marketing.campaign.segment',
                                                   'Sub Campaign Segment'),
        'variable_cost': fields.float('Variable Cost'),
        'revenue': fields.float('Revenue')
        }

   
    def search(self, cr, uid, args, offset=0, limit=None, order=None, 
                                        context=None, count=False):
        if context == None:
            context = {}
        if 'segment_id' in context  and context['segment_id']:
            segment_obj = self.pool.get('marketing.campaign.segment').browse(cr,
                                                    uid, context['segment_id'])
            act_ids = []
            for activity in segment_obj.campaign_id.activity_ids:
                act_ids.append(activity.id)
            return act_ids
        return super(marketing_campaign_activity, self).search(cr, uid, args, 
                                           offset, limit, order, context, count)
    
marketing_campaign_activity()#}}}

class marketing_campaign_transition(osv.osv): #{{{
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"

    _columns = {
        'activity_from_id': fields.many2one('marketing.campaign.activity',
                                                             'Source Activity'),
        'activity_to_id': fields.many2one('marketing.campaign.activity', 
                                                        'Destination Activity'),
        'interval_nbr': fields.integer('Interval No.'),
        'interval_type': fields.selection([('hours', 'Hours'), ('days', 'Days'), 
                                           ('months', 'Months'),
                                            ('years','Years')],'Interval Type')
        }

    def default_get(self, cr, uid, fields, context={}):
        value = super(marketing_campaign_transition, self).default_get(cr, uid,
                                                                fields, context)
        if context.has_key('type_id'):
            value[context['type_id']] = context['activity_id']
        return value
    
marketing_campaign_transition() #}}}

class marketing_campaign_workitem(osv.osv): #{{{
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitem"

    _columns = {
        'segment_id': fields.many2one('marketing.campaign.segment', 'Segment',
                                                        required=True),
        'activity_id': fields.many2one('marketing.campaign.activity','Activity',
                                                        required=True),
        'object_id': fields.related('segment_id', 'campaign_id', 'object_id', 
                                        type='many2one', relation='ir.model', 
                                        string='Object'),
        'res_id': fields.integer('Results'),
        'date': fields.datetime('Execution Date'),
        'partner_id': fields.many2one('res.partner', 'Partner',required=True),
        'state': fields.selection([('todo', 'ToDo'), ('inprogress', 'In Progress'), 
                                   ('exception', 'Exception'), ('done', 'Done'),
                                   ('cancelled', 'Cancelled')], 'State')
        }
    _defaults = {
        'state': lambda *a: 'draft',
    }

    def process_chain(self, cr, uid, workitem_id, context={}):
        workitem = self.browse(cr, uid, workitem_id)
        to_ids = [to_ids.id for to_ids in workitem.activity_id.to_ids]
        mct_obj = self.pool.get('marketing.campaign.transition')
        process_to_id = mct_obj.search(cr,uid, [('id', 'in', to_ids),
                                       ('activity_from_id','=', 'activity_id')])
        for mct_id in mct_obj.browse(cr, uid, process_to_id):
            launch_date = datetime.now() + _intervalTypes[ \
                                    mct_id.interval_type](mct_id.interval_nbr)            
            workitem_vals = {'segment_id': workitem.segment_id.id,
                            'activity_id': mct_id.activity_to_id.id,
                            'date': launch_date,
                            'partner_id': workitem.partner_id.id,
                            'state': 'todo',
                            }
            self.create(cr, uid, workitem_vals)
            
    def process(self, cr, uid, workitem_ids, context={}):
        #for wi in self.browse(cr, uid, workitem_ids):
        #    if wi.state == 'todo'# we searched the wi which are in todo state 
                    #then y v keep this filter again 
        return True
        
    def process_all(self, cr, uid, context={}):
        workitem_ids = self.search(cr, uid, [('state', '=', 'todo'),
                        ('date','<=', time.strftime('%Y-%m-%d %H:%M:%S'))])
        if workitem_ids:
            self.process(cr, uid, workitem_ids, context)
    
marketing_campaign_workitem() #}}}  
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

