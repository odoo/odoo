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

    def _default_stage_id(self):
        return self.env['note.stage'].search([('user_id', '=', self.env.uid)], limit=1)

    memo = fields.Html('Note Content')
    sequence = fields.Integer('Sequence')
    open = fields.Boolean(string='Active', default=True)
    date_done = fields.Date('Date done')
    color = fields.Integer(string='Color Index')

    name = fields.Text(compute='_compute_name', string='Note Summary', store=True)

    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
    stage_ids = fields.Many2many('note.stage', string="User note stages", compute="_compute_stage_ids")

    stage_id = fields.Many2one(
        'note.stage', string='Stage',
        default=_default_stage_id, domain="[('id', 'in', stage_ids)]")
    tag_ids = fields.Many2many('note.tag', 'note_tags_rel', 'note_id', 'tag_id', string='Tags')

    # modifying property of ``mail.thread`` field
    message_partner_ids = fields.Many2many(compute_sudo=True)

    @api.depends('memo')
    def _compute_name(self):
        """ Read the first line of the memo to determine the note name """
        for note in self:
            text = html2plaintext(note.memo) if note.memo else ''
            note.name = text.strip().replace('*', '').split("\n")[0]

    @api.depends('user_id')
    def _compute_stage_ids(self):
        for note in self:
            note.stage_ids = note.user_id.note_stage_ids

    @api.model
    def name_create(self, name):
        return self.create({'memo': name}).name_get()[0]

    def action_close(self):
        return self.write({'open': False, 'date_done': fields.date.today()})

    def action_open(self):
        return self.write({'open': True})
