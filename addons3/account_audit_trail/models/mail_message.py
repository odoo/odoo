# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import fields, models, _
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
    show_audit_log = fields.Boolean(compute="_compute_account_audit_log_move_id", search="_search_show_audit_log")

    def _compute_account_audit_log_preview(self):
        for message in self:
            title = message.subject or message.preview
            tracking_value_ids = message.sudo().tracking_value_ids.filtered(lambda tracking: not tracking.field_groups or self.env.is_superuser() or self.user_has_groups(tracking.field_groups))
            if not title and tracking_value_ids:
                title = _("Updated")
            elif not title and message.subtype_id and not message.subtype_id.internal:
                title = message.subtype_id.display_name
            audit_log_preview = Markup("<div>%s</div>") % title
            for fmt_vals in tracking_value_ids._tracking_value_format():
                field_desc = fmt_vals['changedField']
                old_value = fmt_vals['oldValue']['value']
                new_value = fmt_vals['newValue']['value']
                audit_log_preview += Markup(
                    "<li>%(old_value)s <i class='o_TrackingValue_separator fa fa-long-arrow-right mx-1 text-600' title='%(title)s' role='img' aria-label='%(title)s'></i>%(new_value)s (%(field)s)</li>"
                ) % {
                    'old_value': old_value,
                    'new_value': new_value,
                    'title': _("Changed"),
                    'field': field_desc,
                }
            message.account_audit_log_preview = audit_log_preview

    def _compute_account_audit_log_move_id(self):
        messages_of_account_move = self.filtered(lambda m: m.model == 'account.move' and m.res_id)
        recordset_difference = (self - messages_of_account_move)
        recordset_difference.update({
            'account_audit_log_move_id': False,
            'show_audit_log': False,
        })
        moves = self.env['account.move'].sudo().search([
            ('id', 'in', messages_of_account_move.mapped('res_id')),
            ('company_id.check_account_audit_trail', '=', True),
        ])
        moves_by_id = {m.id: m for m in moves}
        for message in messages_of_account_move:
            message.account_audit_log_move_id = moves_by_id.get(message.res_id, False)
            message.show_audit_log = bool(moves_by_id.get(message.res_id))

    def _search_account_audit_log_move_id(self, operator, value):
        if operator in ['=', 'like', 'ilike', '!=', 'not ilike', 'not like'] and isinstance(value, str):
            res_id_domain = [('res_id', 'in', self.env['account.move']._name_search(value, operator=operator))]
        elif operator in ['=', 'in', '!=', 'not in']:
            res_id_domain = [('res_id', operator, value)]
        else:
            raise UserError(_('Operation not supported'))
        return [('model', '=', 'account.move')] + res_id_domain

    def _search_show_audit_log(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        move_query = self.env['account.move']._search([('company_id.check_account_audit_trail', operator, value)])
        return [('model', '=', 'account.move'), ('res_id', 'in', move_query)]
