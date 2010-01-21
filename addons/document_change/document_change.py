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
        'name': fields.char("Document Change Type", size=64),
        'phase_type_ids': fields.many2many('document.change.process.phase.type','document_process__rel','type_id','change_id','Phase Type'),
        'template_document_id':fields.many2one('ir.attachment','Document')
    }
document_change_type()

class doucment_change_process_phase_type(osv.osv):
    _name = "document.change.process.phase.type"
    _description = "Document Change Process Phase Type"
    
    _columns = {
        'name': fields.char("Document Changed Process Type", size=64),
        'sequence': fields.integer('Sequence'),
        'document_type_ids': fields.many2many('document.change.type','Document','document_phase_process__rel','phase_id','document_id','Phase Type'),
        
    }
doucment_change_process_phase_type()

class doucment_change_process(osv.osv):    
    _name = "document.change.process"
doucment_change_process()

class doucment_change_process_phase(osv.osv):
    _name = "document.change.process.phase"
    _description = "Document Change Process Phase"
    
    _columns = {
        'name': fields.char("Name", size=64),
        'process_id':fields.many2one('document.change.process','Process Change'),
        'sequence': fields.integer('Sequence'),
        'update_document': fields.selection([('at_endPhase', 'At EndPhase'),('at_endprocess', 'At EndPorcess')], 'Update Document', required=True),        
        'type': fields.selection([('required', 'Control Required'),('no_control', 'Control')], 'Type', required=True),
        'date_control': fields.date('Control Date', select=True),        
        'phase_ids':fields.many2one('document.change.process.phase','Phase Type'),
        'state': fields.selection([('draft', 'Draft'),('started', 'Started'),('validate', 'To Validate'), ('end', 'End')], 'Status', readonly=True),
        'phase_document_ids':fields.many2many('ir.attachment','Document','phase_document_rel','phase_id','document_id','Phase Type'),
    }
doucment_change_process_phase()

class document_change_process_model(osv.osv):
    _name = "document.change.process.model"
    _description = "Document Change Process model"
    
    _columns = {
        'name': fields.char("Changed Process Model", size=64,required=True),
        'sequence': fields.integer('Sequence'),
        'phase_type_ids':fields.many2many('document.change.process.phase.type','phase_type_rel','phase_id','phase_model_id','Process Type', required=True),

    }
document_change_process_model()


class document_file(osv.osv):
    _inherit = 'ir.attachment'
    
    _columns = {
        'type_id':fields.many2one('document.change.type','Document Type'),
        'state': fields.selection([('change_request', 'Change Request'),('change_proposed', 'Change Proposed'), ('in_production', 'In Production'), ('to_update', 'To Update'), ('validate', 'To Validate'), ('cancel', 'Cancel')], 'Status', readonly=True),
        'target_document_id': fields.many2one('document.directory', 'Target Document'),
        'target':fields.binary('Target'),
    }
document_file()

class document_change_process_type(osv.osv):
    _name = "document.change.process.type"
    _description = "Document Change Process Type"  
    
    _columns = {
        'name': fields.char("Changed Process Type", size=64),
        }
document_change_process_type()

class doucment_change_process(osv.osv):
    
    _name = "document.change.process"
    _description = "Document Change Process"
    
    def _latestmodification(self, cr, uid, ids, field_name, arg, context={}):
        res = {}
        #TODOto calculate latest modified date from all related documents
        return res
    
    _columns = {
        'name': fields.char("Process Change", size=64),
        'process_type_id' :fields.many2one('document.change.process.type','Type Change'),
        'description': fields.char("Small Description", size=64),
        'change_description':fields.text('Changed Description'),
        'structure_id' :fields.many2one('document.directory','Structure ID'),
        'process_model_id':fields.many2one('document.change.process.model','Process Model'),
        'user_id':fields.many2one('res.users','Change Owner'),
        'create_date':fields.datetime('Creation'),
        'latest_modified_date':fields.function(_latestmodification, method=True, type='date', string="Lastest Modification"), #TODO no year!
        'date_expected':fields.datetime('Expected Production'), 
        'state':fields.selection([('draft', 'Draft'),('progress', 'Progress'),('confirmed', 'To Validate'), ('done', 'Done'),('done', 'Done'),('cancel','Cancelled')], 'Status', readonly=True),
        'process_phase_ids':fields.one2many('document.change.process.phase','process_id','Phase'),
        'process_document_ids': fields.many2many('ir.attachment','document_changed_process_rel','process_id','change_id','Document To Change'), 
    }
doucment_change_process()
