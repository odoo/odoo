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
    """ Category of memo """
    _name = "note.stage"
    _description = "Memo Stage"
    _columns = {
        'name': fields.char('Category Name', size=64, required=True),
        'sequence': fields.integer('Sequence', help="Used to order the memo stages"),
        'user_id': fields.many2one('res.users', 'Owner', help="Owner of the memo stage.", required=True, readonly=True),
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
    """ memo """
    _name = 'note.note'
    _inherit = ['mail.thread']
    _description = "Memo"

    #writing method (no modification of values)
    def _set_note_first_line(self, cr, uid, id, name, value, args={}, context=None):
        return self.write(cr, uid, [id], {'memo': value}, context=context)

    #read the first line (convert hml into text)
    def _get_note_first_line(self, cr, uid, ids, name="", args={}, context=None):
        res = {}
        for note in self.browse(cr, uid, ids, context=context):
            text_note = (note.memo or '').strip().split('\n')[0]
            text_note = re.sub(r'(<br[ /]*>|</p>|</div>)[\s\S]*','',text_note)
            text_note = re.sub(r'<[^>]+>','',text_note)
            res[note.id] = text_note
            
        return res

    #return the default stage for the uid user
    def _get_default_stage_id(self,cr,uid,context=None):
        ids = self.pool.get('note.stage').search(cr,uid,[('user_id','=',uid)])
        return ids and ids[0] or False

    #unactivate a memo and record the date
    def onclick_note_is_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'active' : False, 'date_done' : fields.date.today() })
        
        self.message_post(cr, uid, ids[0], body='This memo is active', subject=False, 
            type='notification', parent_id=False, attachments=None, context=context)

        return False

    #activate a memo
    def onclick_note_not_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, { 'active' : True })

        self.message_post(cr, uid, ids[0], body='This memo is close', subject=False, 
            type='notification', parent_id=False, attachments=None, context=context)

        return False

    #look that the title (first line of the memo) have more of one caracter
    def _constraints_min_len(self, cr, uid, ids, context=None):
        
        res = self._get_note_first_line(cr, uid, ids, context=context)

        for note in self.browse(cr, uid, ids, context=context):
            if len(res[note.id])<1 :
                return False
        
        return True


    #used for undisplay the follower if it's the current user
    def _get_my_current_partner(self, cr, uid, ids, name, args, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        pid = user.partner_id and user.partner_id.id or False
        
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            result[record.id]=pid
        
        return result



    _columns = {
        'name': fields.function(_get_note_first_line, 
            fnct_inv=_set_note_first_line, 
            string='Memo Summary', 
            type='text',
            store=True),
        'memo': fields.html('Pad Content'),
        'sequence': fields.integer('Sequence'),
        # the stage_id depending on the uid
        'stage_id': fields.many2one('note.stage', 'Stage'),

        # ERROR for related & stage_ids => group_by for kanban
        #'stage_id': fields.related('stage_ids', 'id', string='Stage', type="many2one", relation="note.stage"),
        # stage per user
        #'stage_ids': fields.many2many('note.stage','note_stage_rel','note_id','stage_id','Linked stages users'),

        'active': fields.boolean('Active'),
        # when the user unactivate the memo, record de date for un display memo after 1 days
        'date_done': fields.date('Date done'),
        'color': fields.integer('Color Index'),
        # put tags on the memo (optional)
        'tag_ids' : fields.many2many('note.tag','note_tags_rel','note_id','tag_id','Tags'),

        'current_partner_id' : fields.function(_get_my_current_partner),
    }

    _constraints = [
        (_constraints_min_len,'The title (first line on the memo) must have at least one character.',['memo']),
    ]

    _defaults = {
        'active' : 1,
        'stage_id' : _get_default_stage_id,
        'memo': " "
    }
    _order = 'sequence asc'


#upgrade config setting page to configure pad, fancy and tags mode
class note_base_config_settings(osv.osv_memory):
    _inherit = 'base.config.settings'
    _columns = {
        #install of the note_pad module => automatic with "module_"
        'module_note_pad': fields.boolean('Use an etherpad'),
        #auto group user => automatic with "group_"
        'group_note_fancy': fields.boolean('Use fancy render', implied_group='note.group_note_fancy'),
        'group_note_tags': fields.boolean('Use tags for memo', implied_group='note.group_note_tags'),
        'group_note_thread': fields.boolean('Use mail thread and follower', implied_group='note.group_note_thread'),
    }
