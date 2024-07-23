# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import SQL


class PrivacyLookupWizard(models.TransientModel):
    _name = 'privacy.lookup.wizard'
    _description = 'Privacy Lookup Wizard'
    _transient_max_count = 0
    _transient_max_hours = 24

    name = fields.Char(required=True)
    email = fields.Char(required=True)
    line_ids = fields.One2many('privacy.lookup.wizard.line', 'wizard_id')
    execution_details = fields.Text(compute='_compute_execution_details', store=True)
    log_id = fields.Many2one('privacy.log')
    records_description = fields.Text(compute='_compute_records_description')
    line_count = fields.Integer(compute='_compute_line_count')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for wizard in self:
            wizard.line_count = len(wizard.line_ids)

    def _compute_display_name(self):
        self.display_name = _('Privacy Lookup')

    def _get_query_models_blacklist(self):
        return [
            # Already Managed
            'res.partner',
            'res.users',
            # Ondelete Cascade
            'mail.notification',
            'mail.followers',
            'discuss.channel.member',
            # Special case for direct messages
            'mail.message',
        ]

    def _get_query(self):
        name = self.name.strip()
        email = f"%{self.email.strip()}%"
        email_normalized = tools.email_normalize(self.email.strip())

        # Step 1: Retrieve users/partners liked to email address or name
        query = SQL("""
            WITH indirect_references AS (
                SELECT id
                FROM res_partner
                WHERE email_normalized = %s
                OR name ilike %s)
            SELECT
                %s AS res_model_id,
                id AS res_id,
                active AS is_active
            FROM res_partner
            WHERE id IN (SELECT id FROM indirect_references)
            UNION ALL
            SELECT
                %s AS res_model_id,
                id AS res_id,
                active AS is_active
            FROM res_users
            WHERE (
                (login ilike %s)
                OR
                (partner_id IN (
                    SELECT id
                    FROM res_partner
                    WHERE email ilike %s or name ilike %s)))
            -- Step 2: Special case for direct messages
            UNION ALL
            SELECT
                %s AS res_model_id,
                id AS res_id,
                True AS is_active
            FROM mail_message
            WHERE author_id IN (SELECT id FROM indirect_references)
        """,
            # Indirect references CTE
            email_normalized, name,
            # Search on res.partner
            self.env['ir.model.data']._xmlid_to_res_id('base.model_res_partner'),
            # Search on res.users
            self.env['ir.model.data']._xmlid_to_res_id('base.model_res_users'), email, email, name,
            # Direct messages
            self.env['ir.model.data']._xmlid_to_res_id('mail.model_mail_message'),
        )

        # Step 3: Retrieve info on other models
        blacklisted_models = self._get_query_models_blacklist()
        for model_name in self.env:
            if model_name in blacklisted_models:
                continue

            model = self.env[model_name]
            if model._transient or not model._auto:
                continue

            table_name = SQL.identifier(model_name.replace('.', '_'))

            conditions = []
            # 3.1 Search Basic Personal Data Records (aka email/name usage)
            for field_name in ['email_normalized', 'email', 'email_from', 'company_email']:
                if field_name in model and model._fields[field_name].store:
                    rec_name = model._rec_name or 'name'
                    is_normalized = field_name == 'email_normalized' or (model_name == 'mailing.trace' and field_name == 'email')

                    conditions.append(SQL(
                        "%s %s %s",
                        SQL.identifier(field_name),
                        SQL('=') if is_normalized else SQL('ilike'),  # Manage Foo Bar <foo@bar.com>
                        email_normalized if is_normalized else email
                    ))
                    if rec_name in model and model._fields[model._rec_name].store and model._fields[model._rec_name].type == 'char' and not model._fields[model._rec_name].translate:
                        conditions.append(SQL(
                            "%s ilike %s",
                            SQL.identifier(rec_name),
                            name,
                        ))
                    if is_normalized:
                        break

            # 3.2 Search Indirect Personal Data References (aka partner_id)
            conditions.extend(
                SQL(
                    "%s.%s in (SELECT id FROM indirect_references)",
                    table_name,
                    SQL.identifier(field_name),
                )
                for field_name, field in model._fields.items()
                if field.comodel_name == 'res.partner'
                if field.store
                if field.type == 'many2one'
                if field.ondelete != 'cascade'
            )

            if conditions:
                query = SQL("""
                    %s
                    UNION ALL
                    SELECT
                        %s AS res_model_id,
                        id AS res_id,
                        %s AS is_active
                    FROM %s
                    WHERE %s
                """,
                    query,
                    self.env['ir.model'].search([('model', '=', model_name)]).id,
                    SQL.identifier('active') if 'active' in model else True,
                    table_name,
                    SQL(" OR ").join(conditions),
                )
        return query

    def action_lookup(self):
        self.ensure_one()
        query = self._get_query()
        self.env.flush_all()
        self.env.cr.execute(query)
        results = self.env.cr.dictfetchall()
        self.line_ids = [(5, 0, 0)] + [(0, 0, reference) for reference in results]
        return self.action_open_lines()

    def _post_log(self):
        self.ensure_one()
        if not self.log_id and self.execution_details:
            self.log_id = self.env['privacy.log'].create({
                'anonymized_name': self.name,
                'anonymized_email': self.email,
                'execution_details': self.execution_details,
                'records_description': self.records_description,
            })
        else:
            self.log_id.execution_details = self.execution_details
            self.log_id.records_description = self.records_description

    @api.depends('line_ids.execution_details')
    def _compute_execution_details(self):
        for wizard in self:
            wizard.execution_details = '\n'.join(line.execution_details for line in wizard.line_ids if line.execution_details)
            wizard._post_log()

    @api.depends('line_ids')
    def _compute_records_description(self):
        for wizard in self:
            if not wizard.line_ids:
                wizard.records_description = ''
                continue
            records_by_model = defaultdict(list)
            for line in wizard.line_ids:
                records_by_model[line.res_model_id].append(line.res_id)
            wizard.records_description = '\n'.join('{model_name} ({count}): {ids_str}'.format(
                model_name=(f'{model.name} - {model.model}' if self.env.user.has_group('base.group_no_one') else model.name),
                count=len(ids),
                ids_str=', '.join('#%s' % (rec_id) for rec_id in ids),
            ) for model, ids in records_by_model.items())

    def action_open_lines(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('privacy_lookup.action_privacy_lookup_wizard_line')
        action['domain'] = [('wizard_id', '=', self.id)]
        return action


class PrivacyLookupWizardLine(models.TransientModel):
    _name = 'privacy.lookup.wizard.line'
    _description = 'Privacy Lookup Wizard Line'
    _transient_max_count = 0
    _transient_max_hours = 24

    @api.model
    def _selection_target_model(self):
        return [(model.model, model.name) for model in self.env['ir.model'].sudo().search([])]

    wizard_id = fields.Many2one('privacy.lookup.wizard')
    res_id = fields.Integer(
        string="Resource ID",
        required=True)
    res_name = fields.Char(
        string='Resource name',
        compute='_compute_res_name',
        store=True)
    res_model_id = fields.Many2one(
        'ir.model',
        'Related Document Model',
        ondelete='cascade')
    res_model = fields.Char(
        string='Document Model',
        related='res_model_id.model',
        store=True,
        readonly=True)
    resource_ref = fields.Reference(
        string='Record',
        selection='_selection_target_model',
        compute='_compute_resource_ref',
        inverse='_set_resource_ref')
    has_active = fields.Boolean(compute='_compute_has_active', store=True)
    is_active = fields.Boolean()
    is_unlinked = fields.Boolean()
    execution_details = fields.Char(default='')

    @api.depends('res_model', 'res_id', 'is_unlinked')
    def _compute_resource_ref(self):
        for line in self:
            if line.res_model and line.res_model in self.env and not line.is_unlinked:
                # Exclude records that can't be read (eg: multi-company ir.rule)
                try:
                    self.env[line.res_model].browse(line.res_id).check_access_rule('read')
                    line.resource_ref = '%s,%s' % (line.res_model, line.res_id or 0)
                except Exception:
                    line.resource_ref = None
            else:
                line.resource_ref = None

    def _set_resource_ref(self):
        for line in self:
            if line.resource_ref:
                line.res_id = line.resource_ref.id

    @api.depends('res_model_id')
    def _compute_has_active(self):
        for line in self:
            if not line.res_model_id:
                line.has_active = False
                continue
            line.has_active = 'active' in self.env[line.res_model]

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for line in self:
            if not line.res_id or not line.res_model:
                continue
            record = self.env[line.res_model].sudo().browse(line.res_id)
            if not record.exists():
                continue
            name = record.display_name
            line.res_name = name if name else f'{line.res_model_id.name}/{line.res_id}'

    @api.onchange('is_active')
    def _onchange_is_active(self):
        for line in self:
            if not line.res_model_id or not line.res_id:
                continue
            action = _('Unarchived') if line.is_active else _('Archived')
            line.execution_details = '%s %s #%s' % (action, line.res_model_id.name, line.res_id)
            self.env[line.res_model].sudo().browse(line.res_id).write({'active': line.is_active})

    def action_unlink(self):
        self.ensure_one()
        if self.is_unlinked:
            raise UserError(_('The record is already unlinked.'))
        self.env[self.res_model].sudo().browse(self.res_id).unlink()
        self.execution_details = '%s %s #%s' % (_('Deleted'), self.res_model_id.name, self.res_id)
        self.is_unlinked = True

    def action_archive_all(self):
        for line in self:
            if not line.has_active or not line.is_active:
                continue
            line.is_active = False
            line._onchange_is_active()

    def action_unlink_all(self):
        for line in self:
            if line.is_unlinked:
                continue
            line.action_unlink()

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.res_id,
            'res_model': self.res_model,
        }
