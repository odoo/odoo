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

from openerp.osv import osv, fields
from tools.translate import _
import re

class note_stage(osv.osv):
    """ Category of Note """
    _name = "note.stage"
    _description = "Note Stage"
    _columns = {
        'name': fields.char('Category Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Used to order the note stages"),
        'user_id': fields.many2one('res.users', 'Owner', help="Owner of the note stage.", required=True, readonly=True),
        'fold': fields.boolean('Folded'),
    }
    _order = 'sequence asc'
    _defaults = {
        'fold': 0,
        'user_id': lambda self, cr, uid, ctx: uid,
        'sequence' : 1,
    }

class note_tag(osv.osv):

    _name = "note.tag"
    _description = "User can make tags on his note."

    _columns = {
        'name' : fields.char('Tag name', size=64, required=True),
    }

class note_note(osv.osv):
    """ Note """
    _name = 'note.note'
    _inherit = ['mail.thread','pad.common']
    _pad_fields = ['note_pad']
    _description = "Note"

    def _set_note_first_line(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'note': value}, context=context)

    def _get_note_first_line(self, cr, uid, ids, name, args, context=None):
        res = {}
        for note in self.browse(cr, uid, ids, context=context):
            text_note = (note.note or '').strip().split('\n')[0]
            text_note = re.sub(r'(<br[ /]*>|</p>|</div>)[\s\S]*','',text_note)
            text_note = re.sub(r'<[^>]+>','',text_note)
            res[note.id] = text_note
            
        return res

    def _get_default_stage_id(self,cr,uid,context=None):
        ids = self.pool.get('note.stage').search(cr,uid,[('user_id','=',uid)])
        return ids and ids[0] or False

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('note.stage')

        # only show stage groups not folded and owned by user
        search_domain = [('fold', '=', False),('user_id', '=', uid)]

        stage_ids = stage_obj._search(cr, uid, search_domain, order=self._order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        return result

    def onclick_note_is_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'active' : False, 'date_done' : fields.date.today() })
        
        self.message_post(cr, uid, ids[0], body='This note is active', subject=False, 
            type='notification', parent_id=False, attachments=None, context=context)

        return False

    def onclick_note_not_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'active' : True })

        self.message_post(cr, uid, ids[0], body='This note is done', subject=False, 
            type='notification', parent_id=False, attachments=None, context=context)

        return False


    _columns = {
        'name': fields.function(_get_note_first_line, fnct_inv=_set_note_first_line, string='Note Summary', type='text'),
        'note': fields.html('Pad Content'),
        'note_pad_url': fields.char('Pad Url', size=250),
        'sequence': fields.integer('Sequence'),
        # the stage_id depending on the uid
        'stage_id': fields.many2one('note.stage', 'Stage'),

        # ERROR for related & stage_ids => group_by for kanban
        #'stage_id': fields.related('stage_ids', 'id', string='Stage', type="many2one", relation="note.stage"),
        # stage per user
        #'stage_ids': fields.many2many('note.stage','note_stage_rel','note_id','stage_id','Linked stages users'),

        'active': fields.boolean('Active'),
        # when the user unactivate the note, record de date for un display note after 1 days
        'date_done': fields.date('Date done'),
        'color': fields.integer('Color Index'),
        # put tags on the note (optional)
        'tag_ids' : fields.many2many('note.tag','note_tags_rel','note_id','tag_id','Tags'),
    }

    _defaults = {
        'active' : 1,
        'stage_id' : _get_default_stage_id,
        'note_pad_url': lambda self, cr, uid, context: self.pad_generate_url(cr, uid, context),
    }
    _order = 'sequence asc'
    _group_by_full = {
        'stage_id' : _read_group_stage_ids,
    }

