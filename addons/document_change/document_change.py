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


class document_type(osv.osv):
    _name = "document.type"
    _description = "Document Type"
    _columns = {
        'name': fields.char("Document Type", size=64)
        
    }
document_type()

class document_change_type(osv.osv):
    _name = "document.change.type"
    _description = "Document Change Type"
    _columns = {
        'name': fields.char("Document Change Type", size=64),
        'phase_type_ids': many2many('document.change.process.phase.type'),
        'template_document_id': many2one('ir.attachement','Document')
    }
document_change_type()

class doucment_change_process_phase_type(osv.osv):
    _name = "document.change.process.phase.type"
    _description = "Document Change Process Phase Type"
    _columns = {
        'name': fields.char("Document Changed Process Type", size=64),
        'sequence': fields.integer('Sequence'),
        'document_type_ids': many2many('document.type','Document'),
        
    }
doucment_change_process_phase_type()

class document_change_process_model(osv.osv):
    _name = "document.change.process.model"
    _description = "Document Change Process model"
    _columns = {
        'name': fields.char("Changed Process Model", size=64),
        'sequence': fields.integer('Sequence'),
        'phase_type_ids':many2many('document.change.process.phase.type','Change Process Phase Type')

    }
document_change_process_model()


class document_file(osv.osv):
    _inherit = 'ir.attachment'
    _columns = {
        'type_id': many2one('document.change.type')
    }
document_file()

class document_change_process_type(osv.osv):
    _name = "document.change.process.type"
    _description = "Document Change Process Type"  
    _columns = {
        'name': fields.char("Changed Process Type", size=64),

document_change_process_type()
