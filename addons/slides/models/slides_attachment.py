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

class tags(osv.osv):
    _name = 'ir.attachment.tag'

    _columns = {
        'name': fields.char('Name')
    }

class slides_attachment(osv.osv):	
    _inherit = 'ir.attachment'

    _columns = {
        'is_slide': fields.boolean('Is Slide'),
        'tag_ids': fields.many2many('ir.attachment.tag', 'rel_attachment_tags', 'attachment_id', 'tag_id', 'Tags')
    }

    def _default_slides(self, cr, uid, ids, context):
        return context.get('is_slide', False)

    _defaults = {
        'is_slide': _default_slides
    }

    _order = "id desc"
   
    def create(self, cr, uid, values, context=None):
        if values['is_slide']:
            values['url']="/slides/"+values['datas_fname']
        return super(slides_attachment, self).create(cr, uid, values, context)
    
    def write(self, cr, uid, ids, values, context=None):
        datas_fname = self.browse(cr, uid, ids, context=context)[0].datas_fname
        if values['is_slide']:
            values['url']="/slides/"+ datas_fname
        return super(slides_attachment, self).write(cr, uid, ids, values, context)

#TODO: use directory as a category, so if category is not public it can not be displayed on the website
class document_directory(osv.osv):
    _inherit = 'document.directory'

    _columns = {
        'is_public': fields.boolean('Is Public')
    }

    _defaults = {
        'is_slide': False
    }