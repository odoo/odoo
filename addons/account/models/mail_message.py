# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


def _subselect_domain(model, field_name, domain):
    query = model._search(Domain(field_name, '!=', False) & domain, active_test=False, bypass_access=True)
    return Domain('id', 'in', query.subselect(model._field_to_sql(query.table, field_name, query)))


bypass_token = object()
DOMAINS = {
    'res.company':
        lambda rec, operator, value: _subselect_domain(rec.env['account.move.line'], 'company_id',
            Domain('company_id.restrictive_audit_trail', operator, value)
        ),
    'account.move':
        lambda rec, operator, value: [('company_id.restrictive_audit_trail', operator, value)],
    'account.account':
        lambda rec, operator, value: [('used', operator, value), ('company_ids.restrictive_audit_trail', operator, value)],
    'account.tax':
        lambda rec, operator, value: _subselect_domain(rec.env['account.move.line'], 'tax_line_id',
            Domain('company_id.restrictive_audit_trail', operator, value),
        ),
    'res.partner':
        lambda rec, operator, value: _subselect_domain(rec.env['account.move.line'], 'partner_id',
            Domain('company_id.restrictive_audit_trail', operator, value),
        ),
    }


class MailMessage(models.Model):
    _inherit = 'mail.message'

    account_audit_log_preview = fields.Text(
        string="Description",
        compute="_compute_account_audit_log_preview",
        search="_search_account_audit_log_preview",
    )
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
    account_audit_log_restricted = fields.Boolean(
        string="Protected by restricted Audit Logs",
        compute="_compute_account_audit_log_restricted",
        search="_search_account_audit_log_restricted",
    )

    @api.depends('tracking_value_ids')
    def _compute_account_audit_log_preview(self):
        audit_messages = self.filtered(lambda m: m.message_type == 'notification')
        (self - audit_messages).account_audit_log_preview = False
        for message in audit_messages:
            title = message.subject or message.preview
            tracking_value_ids = message.sudo().tracking_value_ids._filter_has_field_access(self.env)
            if not title and tracking_value_ids:
                title = self.env._("Updated")
            if not title and message.subtype_id and not message.subtype_id.internal:
                title = message.subtype_id.display_name
            audit_log_preview = (title or '') + '\n'
            audit_log_preview += "\n".join(
                "%(old_value)s ⇨ %(new_value)s (%(field)s)" % {
                    'old_value': fmt_vals['oldValue'],
                    'new_value': fmt_vals['newValue'],
                    'field': fmt_vals['fieldInfo']['changedField'],
                }
                for fmt_vals in tracking_value_ids._tracking_value_format()
            )
            message.account_audit_log_preview = audit_log_preview

    def _search_account_audit_log_preview(self, operator, value):
        if operator not in ['=', 'like', '=like', 'ilike'] or not isinstance(value, str):
            return NotImplemented

        return Domain('message_type', '=', 'notification') & Domain.OR([
            [('tracking_value_ids.old_value_char', operator, value)],
            [('tracking_value_ids.new_value_char', operator, value)],
            [('tracking_value_ids.old_value_text', operator, value)],
            [('tracking_value_ids.new_value_text', operator, value)],
        ])

    def _compute_account_audit_log_move_id(self):
        self._compute_audit_log_related_record_id('account.move', 'account_audit_log_move_id')

    def _search_account_audit_log_move_id(self, operator, value):
        return self._search_audit_log_related_record_id('account.move', operator, value)

    def _compute_account_audit_log_account_id(self):
        self._compute_audit_log_related_record_id('account.account', 'account_audit_log_account_id')

    def _search_account_audit_log_account_id(self, operator, value):
        return self._search_audit_log_related_record_id('account.account', operator, value)

    def _compute_account_audit_log_tax_id(self):
        self._compute_audit_log_related_record_id('account.tax', 'account_audit_log_tax_id')

    def _search_account_audit_log_tax_id(self, operator, value):
        return self._search_audit_log_related_record_id('account.tax', operator, value)

    def _compute_account_audit_log_company_id(self):
        self._compute_audit_log_related_record_id('res.company', 'account_audit_log_company_id')

    def _search_account_audit_log_company_id(self, operator, value):
        return self._search_audit_log_related_record_id('res.company', operator, value)

    def _compute_account_audit_log_partner_id(self):
        self._compute_audit_log_related_record_id('res.partner', 'account_audit_log_partner_id')

    def _search_account_audit_log_partner_id(self, operator, value):
        return self._search_audit_log_related_record_id('res.partner', operator, value)

    def _compute_account_audit_log_restricted(self):
        self.account_audit_log_restricted = False
        if potentially_restricted := self.filtered(lambda r: r.model in DOMAINS):
            restricted = self.search(Domain('id', 'in', potentially_restricted.ids) + self._search_account_audit_log_restricted('in', [True]))
            restricted.account_audit_log_restricted = True

    def _search_account_audit_log_restricted(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented

        return Domain('message_type', '=', 'notification') & Domain.OR(
            [('model', '=', model), ('res_id', 'in', self.env[model]._search(domain_factory(self, operator, value)))]
            for model, domain_factory in DOMAINS.items()
        )

    def _compute_audit_log_related_record_id(self, model, fname):
        messages_of_related = self.filtered(lambda m: m.model == model and m.res_id)
        (self - messages_of_related)[fname] = False
        for message in messages_of_related:
            message[fname] = message.res_id

    def _search_audit_log_related_record_id(self, model, operator, value):
        if (
            operator in ('like', 'ilike', 'not ilike', 'not like') and isinstance(value, str)
        ) or (
            operator in ('in', 'not in') and any(isinstance(v, str) for v in value)
        ):
            res_id_domain = [('res_id', 'in', self.env[model]._search([('display_name', operator, value)]))]
        elif operator in ('any', 'not any', 'any!', 'not any!'):
            if isinstance(value, Domain):
                query = self.env[model]._search(value)
            else:
                query = value
            res_id_domain = [('res_id', 'in' if operator in ('any', 'any!') else 'not in', query)]
        elif operator in ('in', 'not in'):
            res_id_domain = [('res_id', operator, value)]
        else:
            return NotImplemented
        return [('model', '=', model)] + res_id_domain

    @api.ondelete(at_uninstall=False)
    def _except_audit_log(self):
        if self.env.context.get('bypass_audit') is bypass_token:
            return
        for message in self:
            if message.account_audit_log_move_id and not message.account_audit_log_move_id.posted_before:
                continue
            if message.account_audit_log_restricted:
                raise UserError(self.env._("You cannot remove parts of a restricted audit trail. Archive the record instead."))

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
