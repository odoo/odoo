# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MassMailingListMerge(models.TransientModel):
    _name = 'mass.mailing.list.merge'
    _description = 'Merge Mass Mailing List'

    src_list_ids = fields.Many2many('mail.mass_mailing.list', string='Mailing Lists')
    dest_list_id = fields.Many2one('mail.mass_mailing.list', string='Destination Mailing List')
    merge_options = fields.Selection([
        ('new', 'Merge into a new mailing list'),
        ('existing', 'Merge into an existing mailing list'),
    ], 'Merge Option', required=True, default='new')
    new_list_name = fields.Char('New Mailing List Name')
    archive_src_lists = fields.Boolean('Archive source mailing lists', default=True)

    @api.model
    def default_get(self, fields):
        res = super(MassMailingListMerge, self).default_get(fields)
        src_list_ids = self.env.context.get('active_ids')
        res.update({
            'src_list_ids': src_list_ids,
            'dest_list_id': src_list_ids and src_list_ids[0] or False,
        })
        return res

    def action_mailing_lists_merge(self):
        if self.merge_options == 'new':
            self.dest_list_id = self.env['mail.mass_mailing.list'].create({
                'name': self.new_list_name,
            }).id
        self.dest_list_id.action_merge(self.src_list_ids, self.archive_src_lists)
        return self.dest_list_id
