# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import fields, api, models, _
from odoo.exceptions import UserError


class Message(models.Model):
    _inherit = 'mail.message'

    l10n_in_audit_log_preview = fields.Html(string="Description", compute="_compute_l10n_in_audit_log_preview")
    l10n_in_audit_log_account_move_id = fields.Many2one('account.move', string="Journal Entry", compute="_compute_l10n_in_audit_log_document_name", search="_search_l10n_in_audit_log_document_name")

    @api.depends('body', 'subject', 'tracking_value_ids', 'subtype_id')
    def _compute_l10n_in_audit_log_preview(self):
        for message in self:
            title = message.subject or message.preview
            tracking_value_ids = message.sudo().tracking_value_ids
            if not title and tracking_value_ids:
                title = _("Updated")
            elif not title and message.subtype_id and not message.subtype_id.internal:
                title = message.subtype_id.display_name
            audit_log_preview = Markup("<div>%s</div>") % (title)
            trackings = [
                (
                    fmt_vals['changedField'],
                    fmt_vals['oldValue']['value'],
                    fmt_vals['newValue']['value'],
                ) for fmt_vals in tracking_value_ids._tracking_value_format()
            ]
            for field_desc, old_value, new_value in trackings:
                audit_log_preview += Markup(
                    "<li>%(old_value)s <i class='o_TrackingValue_separator fa fa-long-arrow-right mx-1 text-600' title='%(title)s' role='img' aria-label='%(title)s'></i>%(new_value)s (%(field)s)</li>"
                ) % {
                    'old_value': old_value,
                    'new_value': new_value,
                    'title': _("Changed"),
                    'field': field_desc,
                }
            message.l10n_in_audit_log_preview = audit_log_preview

    @api.depends('model', 'res_id')
    def _compute_l10n_in_audit_log_document_name(self):
        messages_of_account_move = self.filtered(lambda m: m.model == 'account.move' and m.res_id)
        (self - messages_of_account_move).l10n_in_audit_log_account_move_id = False
        moves = self.env['account.move'].search([('id', 'in', messages_of_account_move.mapped('res_id'))])
        moves_by_id = {m.id: m for m in moves}
        for message in messages_of_account_move:
            message.l10n_in_audit_log_account_move_id = moves_by_id.get(message.res_id, False)

    def _search_l10n_in_audit_log_document_name(self, operator, value):
        is_set = False
        if operator == '!=' and isinstance(value, bool):
            is_set = True
        elif operator not in ['=', 'ilike'] or not isinstance(value, str):
            raise UserError(_('Operation not supported'))
        move_domain = [('company_id.account_fiscal_country_id.code', '=', 'IN')]
        if not is_set:
            move_domain += [('name', operator, value)]
        move_query = self.env['account.move']._search(move_domain)
        return [('model', '=', 'account.move'), ('res_id', 'in', move_query)]
