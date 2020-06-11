# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import html2plaintext


class Stage(models.Model):

    _name = "note.stage"
    _description = "Note Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    user_id = fields.Many2one('res.users', string='Owner', required=True, ondelete='cascade', default=lambda self: self.env.uid, help="Owner of the note stage")
    fold = fields.Boolean('Folded by Default')


class Tag(models.Model):

    _name = "note.tag"
    _description = "Note Tag"

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class Note(models.Model):

    _name = 'note.note'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Note"
    _order = 'sequence'

    def _get_default_stage_id(self):
        return self.env['note.stage'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Text(compute='_compute_name', string='Note Summary', store=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
    memo = fields.Html('Note Content')
    sequence = fields.Integer('Sequence')
    stage_id = fields.Many2one('note.stage', compute='_compute_stage_id',
        inverse='_inverse_stage_id', string='Stage', default=_get_default_stage_id)
    stage_ids = fields.Many2many('note.stage', 'note_stage_rel', 'note_id', 'stage_id',
        string='Stages of Users',  default=_get_default_stage_id)
    open = fields.Boolean(string='Active', default=True)
    date_done = fields.Date('Date done')
    color = fields.Integer(string='Color Index')
    tag_ids = fields.Many2many('note.tag', 'note_tags_rel', 'note_id', 'tag_id', string='Tags')
    message_partner_ids = fields.Many2many(
        comodel_name='res.partner', string='Followers (Partners)',
        compute='_get_followers', search='_search_follower_partners',
        compute_sudo=True)
    message_channel_ids = fields.Many2many(
        comodel_name='mail.channel', string='Followers (Channels)',
        compute='_get_followers', search='_search_follower_channels',
        compute_sudo=True)

    @api.depends('memo')
    def _compute_name(self):
        """ Read the first line of the memo to determine the note name """
        for note in self:
            text = html2plaintext(note.memo) if note.memo else ''
            note.name = text.strip().replace('*', '').split("\n")[0]

    def _compute_stage_id(self):
        first_user_stage = self.env['note.stage'].search([('user_id', '=', self.env.uid)], limit=1)
        for note in self:
            for stage in note.stage_ids.filtered(lambda stage: stage.user_id == self.env.user):
                note.stage_id = stage
            # note without user's stage
            if not note.stage_id:
                note.stage_id = first_user_stage

    def _inverse_stage_id(self):
        for note in self.filtered('stage_id'):
            note.stage_ids = note.stage_id + note.stage_ids.filtered(lambda stage: stage.user_id != self.env.user)

    @api.model
    def name_create(self, name):
        return self.create({'memo': name}).name_get()[0]

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if groupby and groupby[0] == "stage_id":
            stages = self.env['note.stage'].search([('user_id', '=', self.env.uid)])
            if stages:  # if the user has some stages
                result = [{  # notes by stage for stages user
                    '__context': {'group_by': groupby[1:]},
                    '__domain': domain + [('stage_ids.id', '=', stage.id)],
                    'stage_id': (stage.id, stage.name),
                    'stage_id_count': self.search_count(domain + [('stage_ids', '=', stage.id)]),
                    '__fold': stage.fold,
                } for stage in stages]

                # note without user's stage
                nb_notes_ws = self.search_count(domain + [('stage_ids', 'not in', stages.ids)])
                if nb_notes_ws:
                    # add note to the first column if it's the first stage
                    dom_not_in = ('stage_ids', 'not in', stages.ids)
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
            else:  # if stage_ids is empty, get note without user's stage
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
        return super(Note, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def action_close(self):
        return self.write({'open': False, 'date_done': fields.date.today()})

    def action_open(self):
        return self.write({'open': True})
