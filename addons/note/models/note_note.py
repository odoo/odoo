# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.tools import html2plaintext

class NoteNote(models.Model):
    """ Note """
    _name = 'note.note'
    _inherit = ['mail.thread']
    _description = "Note"
    _order = 'sequence'

    # return the default stage for the uid user
    def _get_default_stage_id(self):
        return self.env['note.stage'].search([('user_id', '=', self.env.uid)], limit=1).id

    name = fields.Char(compute='_compute_note_first_line', string='Note Summary', store=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
    memo = fields.Html(string='Note Content')
    sequence = fields.Integer()
    stage_id = fields.Many2one('note.stage', compute='_compute_stage_id', inverse='_set_stage_id', default=_get_default_stage_id, string='Stage')
    stage_ids = fields.Many2many('note.stage', 'note_stage_rel', 'note_id', 'stage_id', string='Stages of Users')
    active = fields.Boolean(track_visibility='onchange', default=1)
    date_done = fields.Date()
    color = fields.Integer('Color Index')
    tag_ids = fields.Many2many('note.tag', 'note_tags_rel', 'note_id', 'tag_id', string='Tags')

    #read the first line (convert html into text)
    @api.one
    @api.depends('memo')
    def _compute_note_first_line(self):
        self.name = (self.memo and html2plaintext(self.memo) or "").strip().replace('*', '').split("\n")[0]

    @api.depends('stage_ids.user_id')
    def _compute_stage_id(self):
        for record in self:
            for stage in record.stage_ids.filtered(lambda stage: stage.user_id == self.env.user):
                record.stage_id = stage

    def _set_stage_id(self):
        for record in self:
            if record.stage_id:
                record.stage_ids = record.stage_id + record.stage_ids.filtered(lambda stage: stage.user_id != self.env.user)

    @api.one
    def action_note_is_done(self):
        self.active = 0
        self.date_done = fields.Date.today()

    @api.one
    def action_note_not_done(self):
        self.active = 1
        self.date_done = fields.Date.today()

    #writing method (no modification of values)
    @api.model
    def name_create(self, name):
        record = self.create({'memo': name, })
        return record.name_get()[0]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None,
     context=None, orderby=False, lazy=True):
        if groupby and groupby[0] == "stage_id":
            #search all stages
            stages = self.env['note.stage'].search([('user_id', '=', self.env.uid)])

            if stages:  # if the user has some stages

                result = [{  # notes by stage for stages user
                    '__context': {'group_by': groupby[1:]},
                    '__domain': domain + [('stage_ids.id', '=', stage.id)],
                    'stage_id': (stage.id, stage.name),
                    'stage_id_count': self.search_count(domain + [('stage_ids', '=', stage.id)]),
                    '__fold': stage.fold,
                } for stage in stages]

                #note without user's stage
                nb_notes_ws = self.search_count(domain + [('stage_ids', 'not in', [stage.id for stage in stages])])
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
                            'stage_id_count': nb_notes_ws,
                            '__fold': stages[0].name,
                        }] + result

            else:  # if stage_ids is empty

                #note without user's stage
                nb_notes_ws = self.search_count(domain)
                if nb_notes_ws:
                    result = [{  # notes for unknown stage
                        '__context': {'group_by': groupby[1:]},
                        '__domain': domain,
                        'stage_id': False,
                        'stage_id_count': nb_notes_ws
                    }]
                else:
                    result = []
            return result

        else:
            return super(NoteNote, self).read_group(domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
