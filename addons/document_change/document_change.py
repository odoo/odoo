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
import time
import datetime
import base64

class document_directory(osv.osv):
    _inherit = 'document.directory'
    def _level_compute(self, cr, uid, ids, field_name, arg, context):
        result = {}
        for d in self.browse(cr, uid, ids, context=context):
            result[d.id] = 0
            d2 = d
            while d2:
                d2 = d2.parent_id
                result[d.id] += 1
        return result
    _columns = {
        'level': fields.function(_level_compute, method=True,
            string='level', type='integer', store=True),
    }
document_directory()

class document_change_process_phase_type(osv.osv):
    _name = "document.change.process.phase.type"
document_change_process_phase_type()

class document_change_type(osv.osv):
    _name = "document.change.type"
    _description = "Document Type"
    _columns = {
        'name': fields.char("Document Type", size=64,required=True),
        'phase_type_ids': fields.many2many('document.change.process.phase.type','document_type_phase_type_rel','document_type_id','phase_type_id','Phase Type'),
        'directory_id' :fields.many2one('document.directory','Historic Directory'),
        'filename' :fields.char('Filename', size=128),
        'template_document_id':fields.many2one('ir.attachment','Template Document')
    }
document_change_type()

class document_change_process_phase_type(osv.osv):
    _name = "document.change.process.phase.type"
    _description = "Process Phase Type"
    _columns = {
        'name': fields.char("Process Type", required=True, size=64),
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'document_type_ids': fields.many2many('document.change.type','document_type_phase_type_rel','phase_type_id','document_type_id','Document Type'),
    }
    _defaults = {
        'active': lambda *a:1,
    }
document_change_process_phase_type()

class document_change_process(osv.osv):
    _name = "document.change.process"
document_change_process()

class document_change_process_phase(osv.osv):
    _name = "document.change.process.phase"
    _description = "Process Phase"
    _columns = {
        'name': fields.char("Phase Name", size=64, required=True),
        'process_id':fields.many2one('document.change.process','Process Change'),
        'sequence': fields.integer('Sequence'),
        'update_document': fields.selection([('at_endPhase', 'End Phase'),('at_endprocess', 'End Process')], 'Update Document', required=True),
        'type': fields.selection([('control_required', 'Control Required'),('no_control', 'No Control')], 'Type'),
        'date_control': fields.date('Control Date', select=True),
        'phase_type_id':fields.many2one('document.change.process.phase.type','Phase Type'),
        'directory_id': fields.related('process_id', 'structure_id', relation='document.directory', type="many2one", string='Directory'),
        'state': fields.selection([('draft', 'Draft'),('in_process', 'Started'),('to_validate', 'To Validate'),('done', 'Done')], 'State',readonly=True),
        'phase_document_ids':fields.many2many('ir.attachment','document_change_phase_document', 'phase_id','document_id', 'Documents'),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'update_document': lambda *a:'at_endPhase',
        'type':lambda *a: 'control_required',
    }
    def do_draft(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'draft'})
        return True

    def do_confirm(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'to_validate'})
        return True

    def do_start(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'in_process'})
        todo = []
        for phase in self.browse(cr, uid, ids):
            for doc in phase.phase_document_ids:
                if doc.state in ('draft','in_production'):
                    todo.append(doc.id)
        self.pool.get('ir.attachment').button_request(cr, uid, todo)
        return True

    def do_done(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state':'done'})
        return True
    def test_control_request(self, cr, uid, ids, context=None):
        return all(bool(process.type) =='control_required' for process in self.browse(cr, uid, ids, context=context))

    def test_nocontrol_request(self, cr, uid, ids, context=None):
        return all(bool(process.type) =='no_control' for process in self.browse(cr, uid, ids, context=context))

document_change_process_phase()

class document_change_process_model(osv.osv):
    _name = "document.change.process.model"
    _description = "Process model"

    _columns = {
        'name': fields.char("Model of Process", size=64,required=True),
        'sequence': fields.integer('Sequence'),
        'phase_type_ids':fields.many2many('document.change.process.phase.type','process_model_phase_type_rel','process_model_id','phase_type_id','Phase Type'),
        }
document_change_process_model()

class document_change_process_type(osv.osv):
    _name = "document.change.process.type"
    _description = "Process Type"

    _columns = {
        'name': fields.char("Changed Process Type", size=64),
        }
document_change_process_type()

class document_change_process_email(osv.osv):
    _name = "document.change.process.mail"
    _description = "Process Email Notification"

    _columns = {
        'name': fields.char("Email", size=64),
        'type':fields.selection([('start_end', 'Start/End Process '),('change_all', 'Change in All Document')], 'Notification Type'),
        'process_id':fields.many2one('document.change.process','Process Change'),
        }
document_change_process_email()

class document_change_process(osv.osv):
    _name = "document.change.process"
    _description = "Process"

    def _latestmodification(self, cr, uid, ids, field_name, arg, context={}):
        res = {}
        #TODOto calculate latest modified date from all related documents
        return res

    def _get_document(self, cr, uid, ids, context={}, *arg):
        if not ids:
            return {}
        res = {}
        attach = self.pool.get('ir.attachment')
        directory_obj = self.pool.get('document.directory')
        for process_change in self.browse(cr, uid, ids):
            res1 = []
            for phase_id in  process_change.process_phase_ids:
                res1 += map(lambda x:x.id, phase_id.phase_document_ids or [])
            res[process_change.id] = res1
        return res

    def _get_progress(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        progress = 0.0
        for proc_change in self.browse(cr, uid, ids):
            update_docs = []
            result[proc_change.id] = 0.0
            for doc in proc_change.process_document_ids:
                if doc.state in ('to_update', 'change_propose'):
                    update_docs.append(doc)
                progress = (float(len(update_docs))/float(len(proc_change.process_document_ids)))*100
                result[proc_change.id] = progress
        return result

    def _get_current_phase(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for proc in self.browse(cr, uid, ids):
            result[proc.id] = False
            for phase in proc.process_phase_ids:
                if phase.state in ('in_process','to_validate'):
                    result[proc.id] = phase.id
        return result

    _columns = {
        'name': fields.char("Process ID", size=64, required=True, select=True),
        'process_type_id' :fields.many2one('document.change.process.type','Type of Change'),
        'description': fields.char("Title", size=64, required=True),
        'change_description':fields.text('Changed Description'),
        'structure_id' :fields.many2one('document.directory','Directory', required=True),
        'process_model_id':fields.many2one('document.change.process.model','Process Model'),
        'user_id':fields.many2one('res.users','Owner',required=True),
        'create_date':fields.datetime('Creation',readonly=True),
        'latest_modified_date':fields.function(_latestmodification, method=True, type='datetime', string="Lastest Modification"), #TODO no year!
        'date_expected':fields.datetime('Expected Production'),
        'state':fields.selection([('draft', 'Draft'),('in_progress', 'In Progress'),('to_validate', 'To Validate'), ('pending', 'Pending'), ('done', 'Done'),('cancel','Cancelled')], 'State', readonly=True),
        'process_phase_ids':fields.one2many('document.change.process.phase','process_id','Phase'),
        'current_phase_id': fields.function(_get_current_phase, method=True, type='many2one', relation='document.change.process.phase', string='Current Phase'),
        'date_control': fields.related('current_phase_id','date_control', type='date', string='Control Date'),
        'progress': fields.function(_get_progress, method=True, type='float', string='Progress'),
        'process_document_ids': fields.many2many('ir.attachment','document_changed_process_rel','process_id','change_id','Document To Change'),
    }
    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'document.change.process'),
        'state': lambda *a: 'draft',
        'user_id': lambda laurence,henrion,est,cool: est
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
        directory_obj = self.pool.get('document.directory')
        document_obj = self.pool.get('ir.attachment')
        new_doc_ids = []
        for process in self.browse(cr, uid, ids):
            if not process.process_model_id:
                raise osv.except_osv(_('Error !'), _('You must select a process model !'))
            directory_ids = directory_obj.search(cr, uid, [('parent_id','child_of',process.structure_id and process.structure_id.id)])
            for phase_type_id in process.process_model_id.phase_type_ids:
                new_doc_ids = []
                for document_type_id in phase_type_id.document_type_ids:
                    document_ids = document_obj.search(cr, uid, [
                        ('parent_id','in',directory_ids),
                        ('change_type_id','=',document_type_id.id)
                    ])
                    for document_id in document_ids:
                        vals = {}
                        new_doc_ids.append(document_obj.copy(cr, uid, document_id, vals))
                    if not document_ids:
                        if document_type_id.template_document_id:
                            new_doc_ids.append(document_obj.copy(cr, uid, document_type_id.template_document_id.id, {
                                'name': document_type_id.template_document_id.name,
                                'datas_fname': document_type_id.template_document_id.datas_fname,
                                'parent_id': process.structure_id.id,
                                'change_type_id': document_type_id.id
                            }))
                        else:
                            new_doc_ids.append(document_obj.create(cr, uid, {
                                'name': document_type_id.filename,
                                'datas_fname': document_type_id.filename,
                                'parent_id': process.structure_id.id,
                                'change_type_id': document_type_id.id
                            }))

                phase_value = {
                    'name' : '%s-%s' %(phase_type_id.name, process.name),
                    'sequence': phase_type_id.sequence,
                    'phase_type_id': phase_type_id.id,
                    'process_id': process.id,
                    'phase_document_ids': [(6,0,new_doc_ids)]
                }
                phase_obj.create(cr, uid, phase_value)

        return True

document_change_process()

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    _columns = {
        'change_type_id':fields.many2one('document.change.type','Document Type'),
        'state': fields.selection([('draft','To Create'),('in_production', 'In Production'), ('change_request', 'Change Requested'),('change_propose', 'Change Proposed'), ('to_update', 'To Update'), ('cancel', 'Cancel')], 'State'),
        'style': fields.selection([('run','Run'),('setup','Setup'),('pma','PMA'),('pmp','PMP')],'Document Style'),
        'target':fields.binary('New Document'),
        'process_phase_id':fields.many2many('document.change.process.phase','document_change_phase_document', 'document_id','phase_id', 'Phases'),
        'progress': fields.float('Progress'),
        'change_process_id': fields.related('process_phase_id', 'process_id', type='many2one', relation='document.change.process', string='Change Process'),
    }
    _defaults = {
        'state': lambda *a: 'in_production',
    }

    def _check_duplication(self, cr, uid, vals, ids=[], op='create'):
        name=vals.get('name',False)
        parent_id=vals.get('parent_id',False)
        res_model=vals.get('res_model',False)
        res_id=vals.get('res_id',0)
        type_id=vals.get('change_type_id',False)
        if op=='write':
            for file in self.browse(cr,uid,ids):
                if not name:
                    name=file.name
                if not parent_id:
                    parent_id=file.parent_id and file.parent_id.id or False
                if not res_model:
                    res_model=file.res_model and file.res_model or False
                if not res_id:
                    res_id=file.res_id and file.res_id or 0
                res=self.search(cr,uid,[('id','<>',file.id),('name','=',name),('parent_id','=',parent_id),('res_model','=',res_model),('res_id','=',res_id),('change_type_id','=',type_id)])
                if len(res):
                    return False
        if op=='create':
            res=self.search(cr,uid,[('name','=',name),('parent_id','=',parent_id),('res_id','=',res_id),('res_model','=',res_model),('change_type_id','=',type_id)])
            if len(res):
                return False
        return True

    def button_request(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'change_request'},context=context)
        return True

    def button_propose(self, cr, uid, ids, context={}):
        for attach in self.browse(cr, uid, ids, context=context):
            if not attach.target:
                raise osv.except_osv(_('Error !'), _('You must provide a target content'))
        self.write(cr, uid, ids, {'state':'change_propose'},context=context)
        return True

    def button_validate(self, cr, uid, ids, context={}):
        for attach in self.browse(cr, uid, ids, context=context):
            if not attach.target:
                raise osv.except_osv(_('Error !'), _('You must provide a target content'))
            if (not attach.change_type_id) or not (attach.change_type_id.directory_id.id):
                raise osv.except_osv(_('Configuration Error !'), _('No history directory associated to the document type.'))
            self.copy(cr, uid, [attach.id], {
                'target': False,
                'parent_id': attach.change_type_id.directory_id.id,
                'name': time.strftime('%Y%m%d-%H%M-')+attach.name,
                'datas_fname': time.strftime('%Y%m%d-%H%M-')+attach.datas_fname,
                'state': 'in_production'
            },
            context=context)
            file('/tmp/debug.png','wb+').write(base64.decodestring(attach.target))
            self.write(cr, uid, [attach.id], {
                #'target': False,
                'datas': attach.target,
                'state': 'in_production'
            })
        return True

    def do_production(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'in_production'},context=context)

    def write(self, cr, uid, ids, data, context={}):
        result = super(document_file,self).write(cr,uid,ids,data,context=context)
        for d in self.browse(cr, uid, ids, context=context):
            if d.state=='draft' and d.datas:
                super(document_file,self).write(cr,uid,[d.id],
                    {'state':'in_production'},context=context)
            if (not d.datas) and (d.state=='in_production'):
                super(document_file,self).write(cr,uid,[d.id],
                    {'state':'draft'},context=context)
        return True

    def button_cancel(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'draft'},context=context)

    def button_draft(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state':'draft'},context=context)

document_file()
