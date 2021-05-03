# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MassMailingListMerge(models.TransientModel):
    _name = 'mailing.list.merge'
    _description = 'Merge Mass Mailing List'

    @api.model
    def default_get(self, fields):
        res = super(MassMailingListMerge, self).default_get(fields)

        if not res.get('src_list_ids') and 'src_list_ids' in fields:
            if self.env.context.get('active_model') != 'mailing.list':
                raise UserError(_('You can only apply this action from Mailing Lists.'))
            src_list_ids = self.env.context.get('active_ids')
            res.update({
                'src_list_ids': [(6, 0, src_list_ids)],
            })
        if not res.get('dest_list_id') and 'dest_list_id' in fields:
            src_list_ids = res.get('src_list_ids') or self.env.context.get('active_ids')
            res.update({
                'dest_list_id': src_list_ids and src_list_ids[0] or False,
            })
        return res

    src_list_ids = fields.Many2many('mailing.list', string='Mailing Lists')
    dest_list_id = fields.Many2one('mailing.list', string='Destination Mailing List')
    merge_options = fields.Selection([
        ('new', 'Merge into a new mailing list'),
        ('existing', 'Merge into an existing mailing list'),
    ], 'Merge Option', required=True, default='new')
    new_list_name = fields.Char('New Mailing List Name')
    archive_src_lists = fields.Boolean('Archive source mailing lists', default=True)

    def action_mailing_lists_merge(self):
        if self.merge_options == 'new':
            self.dest_list_id = self.env['mailing.list'].create({
                'name': self.new_list_name,
            }).id
        self.dest_list_id.action_merge(self.src_list_ids, self.archive_src_lists)
        return self.dest_list_id
