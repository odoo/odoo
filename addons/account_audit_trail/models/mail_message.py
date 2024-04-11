# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Message(models.Model):
    _inherit = 'mail.message'

    account_audit_log_preview = fields.Html(string="Description", compute="_compute_account_audit_log_preview")
    account_audit_log_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Journal Entry",
        compute="_compute_account_audit_log_move_id",
        search="_search_account_audit_log_move_id",
    )
    account_audit_log_activated = fields.Boolean(
        string="Audit Log Activated",
        compute="_compute_account_audit_log_activated",
        search="_search_account_audit_log_activated")

    @api.depends('tracking_value_ids')
    def _compute_account_audit_log_preview(self):
        move_messages = self.filtered(lambda m: m.model == 'account.move' and m.res_id)
        (self - move_messages).account_audit_log_preview = False
        for message in move_messages:
            title = message.subject or message.preview
            tracking_value_ids = message.sudo().tracking_value_ids._filter_has_field_access(self.env)
            if not title and tracking_value_ids:
                title = _("Updated")
            if not title and message.subtype_id and not message.subtype_id.internal:
                title = message.subtype_id.display_name
            audit_log_preview = Markup("<div>%s</div>") % (title or '')
            audit_log_preview += Markup("<br>").join(
                Markup(
                    "%(old_value)s <i class='o_TrackingValue_separator fa fa-long-arrow-right mx-1 text-600' title='%(title)s' role='img' aria-label='%(title)s'></i>%(new_value)s (%(field)s)"
                ) % {
                    'old_value': fmt_vals['oldValue']['value'],
                    'new_value': fmt_vals['newValue']['value'],
                    'title': _("Changed"),
                    'field': fmt_vals['changedField'],
                }
                for fmt_vals in tracking_value_ids._tracking_value_format()
            )
            message.account_audit_log_preview = audit_log_preview

    @api.depends('model', 'res_id')
    def _compute_account_audit_log_move_id(self):
        move_messages = self.filtered(lambda m: m.model == 'account.move' and m.res_id)
        (self - move_messages).update({
            "account_audit_log_activated": False,
            "account_audit_log_move_id": False,
        })
        if move_messages:
            moves = self.env['account.move'].sudo().search([
                ('id', 'in', list(set(move_messages.mapped('res_id')))),
                ('company_id.check_account_audit_trail', '=', True),
            ])
            for message in move_messages:
                message.account_audit_log_activated = message.res_id in moves.ids
                message.account_audit_log_move_id = message.res_id in moves.ids and message.res_id

    def _search_account_audit_log_move_id(self, operator, value):
        if operator in ['=', 'like', 'ilike', '!=', 'not ilike', 'not like'] and isinstance(value, str):
            res_id_domain = [('res_id', 'in', self.env['account.move']._name_search(value, operator=operator))]
        elif operator in ['in', '!=', 'not in']:
            res_id_domain = [('res_id', operator, value)]
        else:
            raise UserError(_('Operation not supported'))
        return [('model', '=', 'account.move')] + res_id_domain

    def _search_account_audit_log_activated(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        move_query = self.env['account.move']._search([('company_id.check_account_audit_trail', operator, value)])
        return ['&', ('model', '=', 'account.move'), ('res_id', 'in', move_query)]
