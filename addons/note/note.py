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
from openerp.tools import html2plaintext

class note_stage(osv.osv):
    """ Category of Note """
    _name = "note.stage"
    _description = "Note Stage"
    _columns = {
        'name': fields.char('Stage Name', translate=True, required=True),
        'sequence': fields.integer('Sequence', help="Used to order the note stages"),
        'user_id': fields.many2one('res.users', 'Owner', help="Owner of the note stage.", required=True, ondelete='cascade'),
        'fold': fields.boolean('Folded by Default'),
    }
    _order = 'sequence asc'
    _defaults = {
        'fold': 0,
        'user_id': lambda self, cr, uid, ctx: uid,
        'sequence' : 1,
    }

class note_tag(osv.osv):
    _name = "note.tag"
    _description = "Note Tag"
    _columns = {
        'name' : fields.char('Tag Name', required=True),
    }

class note_note(osv.osv):
    """ Note """
    _name = 'note.note'
    _inherit = ['mail.thread']
    _description = "Note"

    #writing method (no modification of values)
    def name_create(self, cr, uid, name, context=None):
        rec_id = self.create(cr, uid, {'memo': name}, context=context)
        return self.name_get(cr, uid, [rec_id], context)[0]

    #read the first line (convert hml into text)
    def _get_note_first_line(self, cr, uid, ids, name="", args={}, context=None):
        res = {}
        for note in self.browse(cr, uid, ids, context=context):
            res[note.id] = (note.memo and html2plaintext(note.memo) or "").strip().replace('*','').split("\n")[0]

        return res

    def onclick_note_is_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'open': False, 'date_done': fields.date.today()}, context=context)

    def onclick_note_not_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'open': True}, context=context)

    #used for undisplay the follower if it's the current user
    def _get_my_current_partner(self, cr, uid, ids, name, args, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        pid = user.partner_id and user.partner_id.id or False
        return dict.fromkeys(ids, pid)

    #return the default stage for the uid user
    def _get_default_stage_id(self,cr,uid,context=None):
        ids = self.pool.get('note.stage').search(cr,uid,[('user_id','=',uid)], context=context)
        return ids and ids[0] or False

    def _set_stage_per_user(self, cr, uid, id, name, value, args=None, context=None):
        note = self.browse(cr, uid, id, context=context)
        if not value: return False
        stage_ids = [value] + [stage.id for stage in note.stage_ids if stage.user_id.id != uid ]
        return self.write(cr, uid, [id], {'stage_ids': [(6, 0, set(stage_ids))]}, context=context)

    def _get_stage_per_user(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for record in self.browse(cr, uid, ids, context=context):
            for stage in record.stage_ids:
                if stage.user_id.id == uid:
                    result[record.id] = stage.id
        return result

    _columns = {
        'name': fields.function(_get_note_first_line, 
            string='Note Summary', 
            type='text', store=True),
        'memo': fields.html('Note Content'),
        'sequence': fields.integer('Sequence'),
        'stage_id': fields.function(_get_stage_per_user, 
            fnct_inv=_set_stage_per_user, 
            string='Stage', 
            type='many2one', 
            relation='note.stage'),
        'stage_ids': fields.many2many('note.stage','note_stage_rel','note_id','stage_id','Stages of Users'),
        'open': fields.boolean('Active', track_visibility='onchange'),
        'date_done': fields.date('Date done'),
        'color': fields.integer('Color Index'),
        'tag_ids' : fields.many2many('note.tag','note_tags_rel','note_id','tag_id','Tags'),
        'current_partner_id' : fields.function(_get_my_current_partner, type="many2one", relation='res.partner', string="Owner"),
    }
    _defaults = {
        'open' : 1,
        'stage_id' : _get_default_stage_id,
    }
    _order = 'sequence'

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        if groupby and groupby[0]=="stage_id":

            #search all stages
            current_stage_ids = self.pool.get('note.stage').search(cr,uid,[('user_id','=',uid)], context=context)

            if current_stage_ids: #if the user have some stages

                #dict of stages: map les ids sur les noms
                stage_name = dict(self.pool.get('note.stage').name_get(cr, uid, current_stage_ids, context=context))

                result = [{ #notes by stage for stages user
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain + [('stage_ids.id', '=', current_stage_id)],
                        'stage_id': (current_stage_id, stage_name[current_stage_id]),
                        'stage_id_count': self.search(cr,uid, domain+[('stage_ids', '=', current_stage_id)], context=context, count=True)
                    } for current_stage_id in current_stage_ids]

                #note without user's stage
                nb_notes_ws = self.search(cr,uid, domain+[('stage_ids', 'not in', current_stage_ids)], context=context, count=True)
                if nb_notes_ws:
                    # add note to the first column if it's the first stage
                    dom_not_in = ('stage_ids', 'not in', current_stage_ids)
                    if result and result[0]['stage_id'][0] == current_stage_ids[0]:
                        dom_in = result[0]['__domain'].pop()
                        result[0]['__domain'] = domain + ['|', dom_in, dom_not_in]
                    else:
                        # add the first stage column
                        result = [{
                            '__context': {'group_by': groupby[1:]},
                            '__domain': domain + [dom_not_in],
                            'stage_id': (current_stage_ids[0], stage_name[current_stage_ids[0]]),
                            'stage_id_count':nb_notes_ws
                        }] + result

            else: # if stage_ids is empty

                #note without user's stage
                nb_notes_ws = self.search(cr,uid, domain, context=context, count=True)
                if nb_notes_ws:
                    result = [{ #notes for unknown stage
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain,
                        'stage_id': False,
                        'stage_id_count':nb_notes_ws
                    }]
                else:
                    result = []
            return result

        else:
            return super(note_note, self).read_group(self, cr, uid, domain, fields, groupby, 
                offset=offset, limit=limit, context=context, orderby=orderby)


#upgrade config setting page to configure pad, fancy and tags mode
class note_base_config_settings(osv.osv_memory):
    _inherit = 'base.config.settings'
    _columns = {
        'module_note_pad': fields.boolean('Use collaborative pads (etherpad)'),
        'group_note_fancy': fields.boolean('Use fancy layouts for notes', implied_group='note.group_note_fancy'),
    }

class res_users(osv.Model):
    _name = 'res.users'
    _inherit = ['res.users']
    def create(self, cr, uid, data, context=None):
        user_id = super(res_users, self).create(cr, uid, data, context=context)
        user = self.browse(cr, uid, uid, context=context)
        note_obj = self.pool.get('note.stage')
        data_obj = self.pool.get('ir.model.data')
        model_id = data_obj.get_object_reference(cr, uid, 'base', 'group_user') #Employee Group
        group_id = model_id and model_id[1] or False
        if group_id in [x.id for x in user.groups_id]:
            for note_xml_id in ['note_stage_00','note_stage_01','note_stage_02','note_stage_03','note_stage_04']:
                data_id = data_obj._get_id(cr, uid, 'note', note_xml_id)
                stage_id  = data_obj.browse(cr, uid, data_id, context=context).res_id
                note_obj.copy(cr, uid, stage_id, default = { 
                                        'user_id': user_id}, context=context)
        return user_id