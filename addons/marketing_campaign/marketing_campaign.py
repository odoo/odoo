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
    _description = "Marketing Campaigns"
    
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
                                   'State',
                                   readonly=True), 
        'activity_ids': fields.one2many('marketing.campaign.activity', 
                                       'campaign_id', 'Activities'),
        
    }

marketing_campaign()#}}}

class marketing_campaign_segment(osv.osv): #{{{
    _name = "marketing.campaign.segment"
    _description = "Marketing Campaign Segments"

    _columns = {
        'name': fields.char('Name', size=64,required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign', 
                                                required=True),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object'),
        'ir_filter_id':fields.many2one('ir.filters', 'Filter'),
        'sync_last_date': fields.datetime('Date'),
        'sync_mode':fields.selection([('create', 'Create'),
                                      ('write', 'Write')],
                                      'Mode'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('running', 'Running'),
                                   ('done', 'Done'),
                                   ('cancelled', 'Cancelled')],
                                   'State',
                                   readonly=True), 
        'date_run': fields.datetime('Running'),
        'date_done': fields.datetime('Done'),
    }

marketing_campaign_segment()#}}}

class marketing_campaign_activity(osv.osv): #{{{
    _name = "marketing.campaign.activity"
    _description = "Marketing Campaign Activities"

    _columns = {
        'name': fields.char('Name', size=64),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign'),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object'),
        'start': fields.boolean('Start'),
        'condition': fields.text('Condition'),
        'type':fields.selection([('email', 'E-mail'),
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
        'subcampaign_id' :fields.many2one('marketing.campaign', 'Sub-Campaign'),
        'subcampaign_segment_id' :fields.many2one('marketing.campaign.segment',
                                                   'Sub Campaign Segment'),

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
    _description = "Campaign Transitions"

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
    
marketing_campaign_transition() #}}}

class marketing_campaign_workitem(osv.osv): #{{{
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitems"

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

    def process_chain(self, cr, uid, workitem_id, context={}):
        workitem = self.browse(cr, uid, workitem_id)
        to_ids = [to_ids.id for to_ids in workitem.activity_id.to_ids]
        mct_obj = self.pool.get('marketing.campaign.transition')
        process_to_id = mct_obj.search(cr,uid, [('id', 'in', to_ids),
                                       ('activity_from_id','=', 'activity_id')])
        for mct_id in mct_obj.browse(cr, uid, process_to_id):
            launch_date = datetime.datetime.now() + _intervalTypes[ \
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
        workitem_ids = self.search(cr, uid, [('type', '=', 'todo'),
                        ('date','<=', time.strftime('%Y-%m-%d %H:%M:%S'))])
        if workitem_ids:
            self.parocess(cr, uid, workitem_ids, context)
    
marketing_campaign_workitem() #}}}  
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

