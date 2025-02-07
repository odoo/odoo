# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import OR

bypass_token = object()


class Message(models.Model):
    _inherit = 'mail.message'

    account_audit_log_preview = fields.Html(string="Description", compute="_compute_account_audit_log_preview")
    account_audit_log_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Journal Entry",
        compute="_compute_account_audit_log_move_id",
        search="_search_account_audit_log_move_id",
    )
    account_audit_log_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        compute="_compute_account_audit_log_partner_id",
        search="_search_account_audit_log_partner_id",
    )
    account_audit_log_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        compute="_compute_account_audit_log_account_id",
        search="_search_account_audit_log_account_id",
    )
    account_audit_log_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Tax",
        compute="_compute_account_audit_log_tax_id",
        search="_search_account_audit_log_tax_id",
    )
    account_audit_log_company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company ",
        compute="_compute_account_audit_log_company_id",
        search="_search_account_audit_log_company_id",
    )
    account_audit_log_display_name = fields.Char(compute='_compute_account_audit_log_display_name')
    show_audit_log = fields.Boolean(compute="_compute_show_audit_log", search="_search_show_audit_log")

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
        self._compute_audit_log_related_record_id('account.move', 'account_audit_log_move_id', [
            ('company_id.check_account_audit_trail', '=', True),
        ])

    def _search_account_audit_log_move_id(self, operator, value):
        return self._search_audit_log_related_record_id('account.move', operator, value)

    def _compute_account_audit_log_account_id(self):
        self._compute_audit_log_related_record_id('account.account', 'account_audit_log_account_id', [
            ('company_id.check_account_audit_trail', '=', True),
        ])

    def _search_account_audit_log_account_id(self, operator, value):
        return self._search_audit_log_related_record_id('account.account', operator, value)

    def _compute_account_audit_log_tax_id(self):
        self._compute_audit_log_related_record_id('account.tax', 'account_audit_log_tax_id', [
            ('company_id.check_account_audit_trail', '=', True),
        ])

    def _search_account_audit_log_tax_id(self, operator, value):
        return self._search_audit_log_related_record_id('account.tax', operator, value)

    def _compute_account_audit_log_company_id(self):
        self._compute_audit_log_related_record_id('res.company', 'account_audit_log_company_id', [
            ('check_account_audit_trail', '=', True),
        ])

    def _search_account_audit_log_company_id(self, operator, value):
        return self._search_audit_log_related_record_id('res.company', operator, value)

    def _compute_account_audit_log_partner_id(self):
        self._compute_audit_log_related_record_id('res.partner', 'account_audit_log_partner_id', [
            '|', ('company_id', '=', False), ('company_id.check_account_audit_trail', '=', True),
            '|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0),
        ])

    def _search_account_audit_log_partner_id(self, operator, value):
        return self._search_audit_log_related_record_id('res.partner', operator, value)

    def _compute_account_audit_log_display_name(self):
        for message in self:
            message.account_audit_log_display_name = (
                message.account_audit_log_move_id
                or message.account_audit_log_account_id
                or message.account_audit_log_tax_id
                or message.account_audit_log_partner_id
                or message.account_audit_log_company_id
            ).display_name

    def _compute_show_audit_log(self):
        for message in self:
            message.show_audit_log = message.message_type == 'notification' and (
                message.account_audit_log_move_id
                or message.account_audit_log_account_id
                or message.account_audit_log_tax_id
                or message.account_audit_log_partner_id
                or message.account_audit_log_company_id
            )

    def _search_show_audit_log(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        return [('message_type', '=', 'notification')] + OR([
            [('model', '=', 'account.move'), ('res_id', 'in', self.env['account.move']._search([
                ('company_id.check_account_audit_trail', operator, value),
            ]))],
            [('model', '=', 'account.account'), ('res_id', 'in', self.env['account.account']._search([
                ('company_id.check_account_audit_trail', operator, value),
            ]))],
            [('model', '=', 'account.tax'), ('res_id', 'in', self.env['account.tax']._search([
                ('company_id.check_account_audit_trail', operator, value),
            ]))],
            [('model', '=', 'res.partner'), ('res_id', 'in', self.env['res.partner']._search([
                '|', ('company_id', '=', False), ('company_id.check_account_audit_trail', operator, value),
                '|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0),
            ]))],
            [('model', '=', 'res.company'), ('res_id', 'in', self.env['res.company']._search([
                ('check_account_audit_trail', operator, value),
            ]))],
        ])

    def _compute_audit_log_related_record_id(self, model, fname, domain):
        messages_of_related = self.filtered(lambda m: m.model == model and m.res_id)
        (self - messages_of_related)[fname] = False
        if messages_of_related:
            related_recs = self.env[model].sudo().search([('id', 'in', messages_of_related.mapped('res_id'))] + domain)
            recs_by_id = {record.id: record for record in related_recs}
            for message in messages_of_related:
                message[fname] = recs_by_id.get(message.res_id, False)

    def _search_audit_log_related_record_id(self, model, operator, value):
        if operator in ['=', 'like', 'ilike', '!=', 'not ilike', 'not like'] and isinstance(value, str):
            res_id_domain = [('res_id', 'in', self.env[model]._name_search(value, operator=operator))]
        elif operator in ['=', 'in', '!=', 'not in']:
            res_id_domain = [('res_id', operator, value)]
        else:
            raise UserError(_('Operation not supported'))
        return [('model', '=', model)] + res_id_domain

    @api.ondelete(at_uninstall=True)
    def _except_audit_log(self):
        if self.env.context.get('bypass_audit') is bypass_token:
            return
        to_check = self
        partner_message = self.filtered(lambda m: m.account_audit_log_partner_id)
        if partner_message:
            # The audit trail uses the cheaper check on `customer_rank`, but that field could be set
            # without actually having an invoice linked (i.e. creation of the contact through the
            # Invoicing/Customers menu)
            has_related_move = self.env['account.move'].sudo().search_count([
                ('partner_id', 'in', partner_message.account_audit_log_partner_id.ids),
                ('company_id.check_account_audit_trail', '=', True),
            ], limit=1)
            if not has_related_move:
                to_check -= partner_message
        for message in to_check:
            if message.show_audit_log and not (
                message.account_audit_log_move_id
                and not message.account_audit_log_move_id.posted_before
            ):
                raise UserError(_("You cannot remove parts of the audit trail."))

    def write(self, vals):
        # We allow any whitespace modifications in the subject
        normalized_subject = ' '.join(vals['subject'].split()) if vals.get('subject') else None
        if (
            vals.keys() & {'res_id', 'res_model', 'message_type', 'subtype_id'}
            or ('subject' in vals and any(' '.join(s.subject.split()) != normalized_subject for s in self if s.subject))
            or ('body' in vals and any(self.mapped('body')))
        ):
            self._except_audit_log()
        return super().write(vals)
