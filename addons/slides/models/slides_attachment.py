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
import openerp
from openerp.osv import fields, osv

class ir_attachment_tags(osv.osv):
    _name = 'ir.attachment.tag'
    _columns = {
        'name': fields.char('Name')
    }

class document_directory(osv.osv):   
    _inherit = 'document.directory'

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False,
        ),
    }

class ir_attachment(osv.osv):
    _inherit = 'ir.attachment'
    #_inherits = ['mail.thread', 'ir.needaction_mixin']

    _order = "id desc"
    _columns = {
        'is_slide': fields.boolean('Is Slide'),
        'slide_type': fields.selection([('ppt', 'Presentation'), ('doc', 'Document'), ('video', 'Video')], 'Type'),
        'tag_ids': fields.many2many('ir.attachment.tag', 'rel_attachments_tags', 'attachment_id', 'tag_id', 'Tags'),
        'image': fields.binary('Thumb'),
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False,
        ),
    }
    
    def _get_slide_setting(self, cr, uid, context):
        return context.get('is_slide', False)
   
    def _get_slide_type(self, cr, uid, context):
        return context.get('slide_type', 'ppt')

    _defaults = {
        'is_slide': _get_slide_setting,
        'slide_type':_get_slide_type
    }
    
    def create(self, cr, uid, values, context=None):
        if values.get('is_slide', False) and values.get('datas_fname', False):
            values['url']="/slides/"+values['datas_fname']
        id = super(ir_attachment, self).create(cr, uid, values, context)
        return id