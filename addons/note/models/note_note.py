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
        return self.env['note.stage'].search([], limit=1)

    name = fields.Char(compute='_compute_note_first_line', string='Note Summary', store=True)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
    memo = fields.Html(string='Note Content')
    sequence = fields.Integer()
    stage_id = fields.Many2one('note.stage', default=_get_default_stage_id, string='Stage')
    active = fields.Boolean(track_visibility='onchange', default=1)
    date_done = fields.Date()
    color = fields.Integer('Color Index')
    tag_ids = fields.Many2many('note.tag', 'note_tags_rel', 'note_id', 'tag_id', string='Tags')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_obj = self.env['note.stage']
        order = stage_obj._order
        access_rights_uid = access_rights_uid or self._uid

        if read_group_order == 'stage_id desc':
            order = '%s desc' % order

        stage_ids = stage_obj._search([], order=order, access_rights_uid=access_rights_uid)
        result = [stage.name_get()[0] for stage in stage_obj.browse(stage_ids)]

        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(stage_ids):
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    #read the first line (convert html into text)
    @api.one
    @api.depends('memo')
    def _compute_note_first_line(self):
        self.name = (self.memo and html2plaintext(self.memo) or "").strip().replace('*', '').split("\n")[0]

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
