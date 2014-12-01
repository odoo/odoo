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

from openerp import SUPERUSER_ID
from openerp import models, fields, api, exceptions, _
from openerp.tools import html2plaintext

class note_stage(models.Model):
    """ Category of Note """
    _name = "note.stage"
    _description = "Note Stage"

    name = fields.Char('Stage Name', translate=True, required=True)
    sequence = fields.Integer('Sequence', help="Used to order the note stages", default=1)
    user_id = fields.Many2one('res.users', 'Owner', help="Owner of the note stage.", required=True, ondelete='cascade', default=lambda self: self.env.user)
    fold = fields.Boolean('Folded by Default', default=0)

    _order = 'sequence asc'

class note_tag(models.Model):
    _name = "note.tag"
    _description = "Note Tag"
    name = fields.Char('Tag Name', required=True)

class note_note(models.Model):
    """ Note """
    _name = 'note.note'
    _inherit = ['mail.thread']
    _description = "Note"

    #writing method (no modification of values)
    #overwrite models.Model.name_create(): creates a new record with only the name provided
    @api.model
    def name_create(self, name):
        stage_id = self.env.context['default_stage_id']
        rec_id = self.create({'memo': name, 'stage_ids':[(6,0,[stage_id])]})
        return rec_id.name_get()[0]

    #read the first line (convert hml into text)
    @api.one
    @api.depends('memo')
    def _get_note_first_line(self):
        self.name = (self.memo and html2plaintext(self.memo) or "").strip().replace('*','').split("\n")[0]

    @api.one
    def onclick_note_is_done(self):
        self.open = 0
        self.date_done = fields.Date.today()

    @api.one
    def onclick_note_not_done(self):
        self.open = 1

    #return the default stage for the uid user
    def _get_default_stage_id(self):
        ids = self.env['note.stage'].search([('user_id','=',self.env.uid)])
        return ids and ids[0] or False

    def _set_stage_per_user(self):
        self.stage_ids = [(6,0, [self.stage_id.id] + [stage.id for stage in self.stage_ids if stage.user_id.id != self.env.uid ])]

    @api.one
    def _get_stage_per_user(self):
        for stage in self.stage_ids:
            if stage.user_id.id == self.env.uid:
                self.stage_id = stage
            else:
                self.stage_id =  False


    name= fields.Text(compute ='_get_note_first_line',
                      string='Note Summary',
                      store=True)
    user_id = fields.Many2one('res.users', 'Owner', default=lambda self: self.env.user)
    memo = fields.Html('Note Content')
    sequence = fields.Integer()
    stage_id = fields.Many2one('note.stage',
                               compute = '_get_stage_per_user',
                               inverse = '_set_stage_per_user',
                               default = _get_default_stage_id,
                               string='Stage')
    stage_ids = fields.Many2many('note.stage','note_stage_rel','note_id','stage_id','Stages of Users')
    open = fields.Boolean('Active', track_visibility='onchange', default = 1)
    date_done = fields.Date('Date done')
    color = fields.Integer('Color Index')
    tag_ids = fields.Many2many('note.tag','note_tags_rel','note_id','tag_id','Tags')

    _order = 'sequence'

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        if groupby and groupby[0]=="stage_id":
            #search all stages
            stages = self.env['note.stage'].search([('user_id','=',self.env.uid)])

            if stages: #if the user has some stages

                result = [{ #notes by stage for stages user
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain + [('stage_ids.id', '=', stage.id)],
                        'stage_id': (stage.id, stage.name),
                        'stage_id_count': self.search_count(domain+[('stage_ids', '=', stage.id)]),
                        '__fold': stage.fold,
                    } for stage in stages]

                #note without user's stage
                nb_notes_ws = self.search_count(domain+[('stage_ids', 'not in',  [stage.id for stage in stages])])
                if nb_notes_ws:
                    # add note to the first column if it's the first stage
                    dom_not_in = ('stage_ids', 'not in', [stage.id for stage in stages])
                    if result and result[0]['stage_id'][0] == stages[0].id:
                        dom_in = result[0]['__domain'].pop()
                        result[0]['__domain'] = domain + ['|', dom_in, dom_not_in]
                        result[0]['stage_id_count'] += nb_notes_ws
                    else:
                        # add the first stage column
                        result = [{
                            '__context': {'group_by': groupby[1:]},
                            '__domain': domain + [dom_not_in],
                            'stage_id': (stages[0].id, stages[0].name),
                            'stage_id_count':nb_notes_ws,
                            '__fold': stages[0].name,
                        }] + result

            else: # if stage_ids is empty

                #note without user's stage
                nb_notes_ws = self.search_count(domain)
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
            return super(note_note, self).read_group(self, self.env.cr, self.env.uid, domain, fields, groupby,
                offset=offset, limit=limit, context=context, orderby=orderby,lazy=lazy)

#upgrade config setting page to configure pad
class note_base_config_settings(models.TransientModel):
    _inherit = 'base.config.settings'
    module_note_pad = fields.Boolean('Use collaborative pads (etherpad)')

class res_users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def create(self, data):
        user = super(res_users, self).create(data)
        note_obj = self.env['note.stage'].search([('user_id','=',SUPERUSER_ID)])
        data_obj = self.env['ir.model.data']
        is_employee = self.has_group('base.group_user')
        if is_employee:
            note_obj.copy(default={'user_id': user.id})
        return user
