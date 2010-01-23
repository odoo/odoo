#-*- coding: utf-8 -*-
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
import tools
from osv import fields, osv
import os
import pooler
import netsvc
from tools.translate import _

class doucment_change_process_phase_type(osv.osv):
 _name = "document.change.process.phase.type"
doucment_change_process_phase_type()

class document_change_type(osv.osv):
    _name = "document.change.type"
    _description = "Document Change Type"
    
    _columns = {
        'name': fields.char("Document Change Type", size=64,required=True),
        'phase_type_ids': fields.many2many('document.change.process.phase.type','document_type_phase_type_rel','document_type_id','phase_type_id','Phase Type'),
        'template_document_id':fields.many2one('ir.attachment','Document')
    }
document_change_type()

class doucment_change_process_phase_type(osv.osv):
    _name = "document.change.process.phase.type"
    _description = "Document Change Process Phase Type"
    
    _columns = {
        'name': fields.char("Document Changed Process Type", size=64),
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'document_type_ids': fields.many2many('document.change.type','phase_type_document_type_rel','phase_type_id','document_type_id','Document Type'),
    }
doucment_change_process_phase_type()

class doucment_change_process(osv.osv):    
    _name = "document.change.process"
doucment_change_process()

class doucment_change_process_phase(osv.osv):
    _name = "document.change.process.phase"
    _description = "Document Change Process Phase"
    
    _columns = {
        'name': fields.char("Name", size=64, required=True),
        'process_id':fields.many2one('document.change.process','Process Change'),
        'sequence': fields.integer('Sequence'),
        'update_document': fields.selection([('at_endPhase', 'End Phase'),('at_endprocess', 'End Process')], 'Update Document', required=True),        
        'type': fields.selection([('control_required', 'Control Required'),('no_control', 'No Control')], 'Type'),
        'date_control': fields.date('Control Date', select=True),        
        'phase_type_id':fields.many2one('document.change.process.phase.type','Phase Type'),
        'state': fields.selection([('draft', 'Draft'),('in_process', 'Started'),('to_validate', 'To Validate'),('done', 'Done')], 'State',readonly=True),
        'phase_document_ids':fields.many2many('ir.attachment','phase_document_rel','phase_id','document_id','Document'),
    }
    _defaults = {      
     'state': lambda *a: 'draft',
     'update_document': lambda *a:'at_endPhase',
     'type':lambda *a: 'no_control',
     }
    def do_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def do_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'to_validate'})
        return True

    def do_start(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'in_process'})
        return True           

    def do_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'done'})
        return True 

doucment_change_process_phase()

class document_change_process_model(osv.osv):
    _name = "document.change.process.model"
    _description = "Document Change Process model"
    
    _columns = {
        'name': fields.char("Changed Process Model", size=64,required=True),
        'sequence': fields.integer('Sequence'),
        'phase_type_ids':fields.many2many('document.change.process.phase.type','process_model_phase_type_rel','process_model_id','phase_type_id','Phase Type'),
        }
document_change_process_model()

class document_change_process_type(osv.osv):
    _name = "document.change.process.type"
    _description = "Document Change Process Type"  
    
    _columns = {
        'name': fields.char("Changed Process Type", size=64),
        }
document_change_process_type()

class document_change_process_email(osv.osv):
    _name = "document.change.process.mail"
    _description = "Document Change Process Email Notification"  
    
    _columns = {
        'name': fields.char("Email", size=64),
        'type':fields.selection([('start_end', 'Start/End Process '),('change_all', 'Change in All Document')], 'Notification Type'),
        'process_id':fields.many2one('document.change.process','Process Change'),        
        }
document_change_process_email()

class doucment_change_process(osv.osv):
    
    _name = "document.change.process"
    _description = "Document Change Process"
    
    def _latestmodification(self, cr, uid, ids, field_name, arg, context={}):
        res = {}
        #TODOto calculate latest modified date from all related documents
        return res
    
    _columns = {
        'name': fields.char("Process Change", size=64, required=True, select=True),
        'process_type_id' :fields.many2one('document.change.process.type','Type Change'),
        'description': fields.char("Small Description", size=64),
        'change_description':fields.text('Changed Description'),
        'structure_id' :fields.many2one('document.directory','Structure ID'),
        'process_model_id':fields.many2one('document.change.process.model','Process Model'),
        'user_id':fields.many2one('res.users','Change Owner'),
        'create_date':fields.datetime('Creation',readonly=True),
        'latest_modified_date':fields.function(_latestmodification, method=True, type='date', string="Lastest Modification"), #TODO no year!
        'date_expected':fields.datetime('Expected Production'), 
        'state':fields.selection([('draft', 'Draft'),('in_progress', 'In Progress'),('to_validate', 'To Validate'), ('pending', 'Pending'), ('done', 'Done'),('cancel','Cancelled')], 'state', readonly=True),
        'process_phase_ids':fields.one2many('document.change.process.phase','process_id','Phase'),        
        'pending_directory_id' :fields.many2one('document.directory','Pending Directory ID'),   
        'date_control': fields.date('Control Date'), #TODO: make relate field with current_phase_id.date_control
        'progress': fields.float('Progress'), #TODO : functio field: calculate progress
        'current_phase_id': fields.many2one('document.change.process.phase','Current Phase'), # TODO: function field. find out in process phase 
        'process_document_ids': fields.many2many('ir.attachment','document_changed_process_rel','process_id','change_id','Document To Change'),
    }
    _defaults = {      
      'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'document.change.process'),
      'state': lambda *a: 'draft',
      }
    def do_start(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'in_progress'},context=context)              
        return True

    def do_pending(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'pending'},context=context)                
        return True             
    
    def do_confirm(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'to_validate'},context=context)
        return True   

    def do_done(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done'},context=context)
        return True   
             
    def do_cancel(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'cancel'},context=context) 

    def generate_phases(self, cr, uid, ids, *args):
        phase_obj = self.pool.get('document.change.process.phase')
        phase_type_obj = self.pool.get('document.change.process.phase.type')  
        document_type_obj = self.pool.get('document.change.type') 
        document_obj = self.pool.get('ir.attachment')     
        for process in self.browse(cr, uid, ids):
            if process.process_model_id:
                for phase_type_id in process.process_model_id.phase_type_ids:
                    phase_type = phase_type_obj.browse(cr, uid, phase_type_id)
                    phase_value = {
                        'name' : '%s-%s' %(phase_type, process.name),
                        'phase_type_id': phase_type_id,
                        'process_id': process.id   
                        }            
                    phase_id = phase_obj.create(cr, uid, phase_value)
                    cr.execute('select document_type_id from document_type_phase_type_rel where phase_type_id = %s' ,phase_type_id)
                    document_type_ids = map(lambda x: x[0], cr.fetchall())
                    document_ids = document_obj.search(cr, uid, [
                            ('parent_id','=',process.structure_id and process.structure_id.id),
                            ('change_type_id','in',document_type_ids)])
                    for document_id in document_ids:
                        vals = {'process_phase_id':phase_id}
                        if process.pending_directory_id:
                            vals.update({'parent_id':process.pending_directory_id.id})
                        document_obj.copy(cr, uid, document_id, vals)
                     
    
doucment_change_process()

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    
    _columns = {
        'change_type_id':fields.many2one('document.change.type','Document Type'),
        'state': fields.selection([('in_production', 'In Production'), ('change_request', 'Change Request'),('change_propose', 'Change Proposed'), ('to_update', 'To Update'), ('cancel', 'Cancel')], 'State'),
        'target_directory_id': fields.many2one('document.directory', 'Target Document'),
        'target_document_id':fields.binary('Target'),
        'process_phase_id' :fields.many2one('document.change.process.phase','Process Phase'),
        'progress': fields.float('Progress'), #TODO : functio field: calculate progress
        'change_process_id': fields.related('process_phase_id', 'process_id', type='many2one', relation='document.change.process', string='Change Process'),
    }
    _defaults = {      
        'state': lambda *a: 'in_production',
     }    
    def do_change_request(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'change_request'},context=context)              
        return True

    def do_change_propose(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'change_propose'},context=context)                
        return True             
    
    def do_to_update(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'to_update'},context=context)
        return True   

    def do_production(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'in_production'},context=context)
        return True   
             
    def do_cancel(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'cancel'},context=context)        
        
document_file()
