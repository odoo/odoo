# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models, _
from odoo.exceptions import UserError
from odoo.tools import html_escape


class Message(models.Model):
    _inherit = 'mail.message'

    l10n_in_audit_log_preview = fields.Html(string="Description", compute="_compute_l10n_in_audit_log_preview")
    l10n_in_audit_log_document_name = fields.Html(string="Document number", compute="_compute_l10n_in_audit_log_document_name", search="_search_l10n_in_audit_log_document_name")

    @api.depends('body', 'subject', 'tracking_value_ids', 'subtype_id')
    def _compute_l10n_in_audit_log_preview(self):
        for message in self:
            title = message.description
            # Tracking value model rights only for admins so use sudo same done in _message_format to show tracking values
            tracking_value_ids = message.sudo().tracking_value_ids
            if not title and tracking_value_ids:
                title = _("Updated")
            elif not title and message.subtype_id and not message.subtype_id.internal:
                title = html_escape(message.subtype_id.display_name)
            audit_log_preview = "<div>%s</div>" % (title)
            for value in tracking_value_ids:
                audit_log_preview += _("<li>%s <i class='o_TrackingValue_separator fa fa-long-arrow-right\
                            mx-1 text-600' title='Changed' role='img' aria-label='Changed'></i>\
                            %s (%s)</li>", value.get_old_display_value()[0], value.get_new_display_value()[0], value.field.field_description)
            message.l10n_in_audit_log_preview = audit_log_preview

    @api.depends('model', 'res_id')
    def _compute_l10n_in_audit_log_document_name(self):
        messages_of_account_move = self.filtered(lambda m: m.model == 'account.move' and m.res_id)
        (self - messages_of_account_move).l10n_in_audit_log_document_name = False
        moves = self.env['account.move'].search_read([('id', 'in', messages_of_account_move.mapped('res_id'))], ['display_name'])
        move_names = {m['id']: m['display_name'] for m in moves}
        for message in messages_of_account_move:
            message.l10n_in_audit_log_document_name = move_names[message.res_id]

    def _search_l10n_in_audit_log_document_name(self, operator, value):
        if operator not in ['=', 'ilike'] or not isinstance(value, str):
            raise UserError(_('Operation not supported'))
        moves = self.env['account.move'].search([('name', operator, value)])
        return [('model', '=', 'account.move'), ('res_id', 'in', moves.ids)]

    def action_open_document(self):
        """ Opens the related record based on the model and ID """
        self.ensure_one()
        return {
            'res_id': self.res_id,
            'res_model': self.model,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
        }
