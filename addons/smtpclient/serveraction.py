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

from osv import osv
from osv import fields
import netsvc
import time

class email_headers(osv.osv):
    _inherit = 'email.headers'
    _columns = {
        'action_id':fields.many2one('ir.actions.server', 'Server Action'),
    }
email_headers()

class server_action(osv.osv):
    _inherit = 'ir.actions.server'
    _description = 'Email Client'
    _columns = {
        'email_server':fields.many2one('email.smtpclient', 'Email Server'),
        'report_id':fields.many2one('ir.actions.report.xml', 'Report', required=False),
        'file_ids':fields.many2many('ir.attachment', 'serveraction_attachment_rel', 'action_id', 'file_id', 'Attachments'),
        'header_ids':fields.one2many('email.headers', 'action_id', 'Default Headers'),
    }
    
    def run(self, cr, uid, ids, context={}):
        logger = netsvc.Logger()
        
        act_ids = []
        
        for action in self.browse(cr, uid, ids, context):
            obj_pool = self.pool.get(action.model_id.model)
            obj = obj_pool.browse(cr, uid, context['active_id'], context=context)
            cxt = {
                'context':context, 
                'object': obj, 
                'time':time,
                'cr': cr,
                'pool' : self.pool,
                'uid' : uid
            }
            expr = eval(str(action.condition), cxt)
            if not expr:
                continue

            if action.state == 'email':                
                address = str(action.email)
                try:
                    address =  eval(str(action.email), cxt)
                except:
                    pass

                if not address:
                    logger.notifyChannel('email', netsvc.LOG_INFO, 'Partner Email address not Specified!')
                    continue

                subject = self.merge_message(cr, uid, action.subject, action, context)
                body = self.merge_message(cr, uid, action.message, action, context)
                smtp_pool = self.pool.get('email.smtpclient')

                reports = []
                if action.report_id:
                    reports.append(('report.'+action.report_id.report_name, [context['active_id']]))
                
                ir_attach_ids = []
                if action.file_ids:
                    for ir_file in action.file_ids:
                        ir_attach_ids.append(ir_file.id)
                
                headers = { }
                for key in action.header_ids:
                    val = eval(key.value, cxt)
                    headers[key.key] = val
                
                context['headers'] = headers
                
                if smtp_pool.send_email(cr, uid, action.email_server.id, address, subject, body, [], reports=reports, ir_attach=ir_attach_ids, context=context) == True:
                    logger.notifyChannel('smtp', netsvc.LOG_INFO, 'Email successfully send to : %s' % (address))
                else:
                    logger.notifyChannel('smtp', netsvc.LOG_ERROR, 'Failed to send email to : %s' % (address))

            else:
                act_ids.append(action.id)
        
        if act_ids:
            return super(server_action,self).run(cr, uid, act_ids, context)
        else:
            return False

server_action()
