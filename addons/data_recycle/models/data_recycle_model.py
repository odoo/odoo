# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, modules
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import _, split_every

# When recycle_mode = automatic, _recycle_records calls action_validate.
# This is quite slow so requires smaller batch size.
DR_CREATE_STEP_AUTO = 5000
DR_CREATE_STEP_MANUAL = 50000


class Data_RecycleModel(models.Model):
    _name = 'data_recycle.model'
    _description = 'Recycling Model'
    _order = 'name'

    base_id = fields.Many2one('data_cleaning.base', string='Cleaning Base', required=True,
                                 ondelete='cascade', index='btree_not_null')

    active = fields.Boolean(related='base_id.active')
    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False, required=True, copy=True)

    res_model_id = fields.Many2one(related='base_id.res_model_id')
    res_model_name = fields.Char(related='base_id.res_model_name', string='Model Name', readonly=True, store=True)
    recycle_record_ids = fields.One2many('data_recycle.record', 'recycle_model_id')

    recycle_mode = fields.Selection(related='base_id.cleaning_mode')
    recycle_action = fields.Selection([
        ('archive', 'Archive'),
        ('unlink', 'Delete'),
    ], string="Recycle Action", default='unlink', required=True)

    # Rule
    domain = fields.Char(string="Filter", compute='_compute_domain', readonly=False, store=True)
    time_field_id = fields.Many2one(
        'ir.model.fields', string='Time Field',
        domain="[('model_id', '=', res_model_id), ('ttype', 'in', ('date', 'datetime')), ('store', '=', True)]",
        ondelete='cascade')
    time_field_delta = fields.Integer(string='Delta', default=1)
    time_field_delta_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')], string='Delta Unit', default='months')

    records_to_recycle_count = fields.Integer(
        'Records To Recycle', compute='_compute_records_to_recycle_count')

    # User Notifications for Manual clean
    notify_user_ids = fields.Many2many(related='base_id.notify_user_ids')
    notify_frequency = fields.Integer(related='base_id.notify_frequency')
    notify_frequency_period = fields.Selection(related='base_id.notify_frequency_period')
    last_notification = fields.Datetime(related='base_id.last_notification')

    @api.constrains('recycle_action')
    def _check_recycle_action(self):
        for model in self:
            if model.recycle_action == 'archive' and 'active' not in self.env[model.res_model_name]:
                raise UserError(_("This model doesn't manage archived records. Only deletion is possible."))

    @api.depends('res_model_id')
    def _compute_name(self):
        for model in self:
            if not model.name:
                model.name = model.res_model_id.name

    @api.depends('res_model_id')
    def _compute_domain(self):
        self.domain = '[]'

    def _compute_records_to_recycle_count(self):
        count_data = self.env['data_recycle.record']._read_group(
            [('recycle_model_id', 'in', self.ids)],
            ['recycle_model_id'],
            ['__count'])
        counts = {recycle_model.id: count for recycle_model, count in count_data}
        for model in self:
            model.records_to_recycle_count = counts[model.id] if model.id in counts else 0

    def _recycle_records(self, batch_commits=False):
        self.env.flush_all()
        records_to_clean = []
        is_test = modules.module.current_test

        existing_recycle_records = self.env['data_recycle.record'].with_context(
            active_test=False).search([('recycle_model_id', 'in', self.ids)])
        mapped_existing_records = defaultdict(list)
        for recycle_record in existing_recycle_records:
            mapped_existing_records[recycle_record.recycle_model_id].append(recycle_record.res_id)

        for recycle_model in self:
            rule_domain = Domain(ast.literal_eval(recycle_model.domain)) if recycle_model.domain and recycle_model.domain != '[]' else Domain.TRUE
            if recycle_model.time_field_id and recycle_model.time_field_delta and recycle_model.time_field_delta_unit:
                if recycle_model.time_field_id.ttype == 'date':
                    now = fields.Date.today()
                else:
                    now = fields.Datetime.now()
                delta = relativedelta(**{recycle_model.time_field_delta_unit: recycle_model.time_field_delta})
                rule_domain &= Domain(recycle_model.time_field_id.name, '<=', now - delta)
            model = self.env[recycle_model.res_model_name]
            records_to_recycle = model.search(rule_domain)

            # Get IDs of records currently matching the recycle rule (current_ids)
            # and IDs of records already in the recycle records (existing_ids).
            current_ids = set(records_to_recycle.ids)
            existing_ids = set(mapped_existing_records[recycle_model])
            # Remove recycle records for records that no longer match the recycle rule.
            ids_to_remove = existing_ids - current_ids

            if ids_to_remove:
                self.env['data_recycle.record'].search([
                    ('recycle_model_id', '=', recycle_model.id),
                    ('res_id', 'in', ids_to_remove)
                ]).unlink()

            records_to_create = [{
                'res_id': record.id,
                'recycle_model_id': recycle_model.id,
            } for record in records_to_recycle if record.id not in existing_ids]

            if recycle_model.recycle_mode == 'automatic':
                existing_records = self.env['data_recycle.record'].search([
                    ('recycle_model_id', '=', recycle_model.id)
                ])
                for idx in range(0, len(existing_records), DR_CREATE_STEP_AUTO):
                    existing_batch = existing_records[idx:idx + DR_CREATE_STEP_AUTO]
                    existing_batch.action_validate()
                    if batch_commits and not is_test:
                        self.env.cr.commit()
                for records_to_create_batch in split_every(DR_CREATE_STEP_AUTO, records_to_create):
                    self.env['data_recycle.record'].create(records_to_create_batch).action_validate()
                    if batch_commits and not is_test:
                        # Commit after each batch iteration to avoid complete rollback on timeout as
                        # this can create lots of new records.
                        self.env.cr.commit()
            else:
                records_to_clean = records_to_clean + records_to_create
        for records_to_clean_batch in split_every(DR_CREATE_STEP_MANUAL, records_to_clean):
            self.env['data_recycle.record'].create(records_to_clean_batch)
            if batch_commits and not is_test:
                self.env.cr.commit()

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['data_recycle.record'].search([('recycle_model_id', 'in', self.ids)]).unlink()
        result = super().write(vals)
        self._refresh_records_to_process(vals)
        return result

    def _refresh_records_to_process(self, vals):
        # Regenerate the recycle records (with their count) when the matching
        # configuration changes, mirroring the work the stat button triggers on click.
        if not {'domain', 'time_field_id', 'time_field_delta', 'time_field_delta_unit', 'recycle_action'}.isdisjoint(vals):
            self.sudo()._recycle_records()

    def open_records(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("data_recycle.action_data_recycle_record")
        action['context'] = dict(ast.literal_eval(action.get('context')), searchpanel_default_recycle_model_id=self.id)
        action['domain'] = [('recycle_model_id', '=', self.id)]
        return action

    def action_recycle_records(self):
        self.sudo()._recycle_records()
        if self.recycle_mode == 'manual':
            return self.open_records()
        return

    def refresh_recycle_records(self):
        """
        Refresh recycled records and reopen the Data Recycle view.
        Preserves the selected search panel filter by passing
        `recycle_model_id` into the action context.
        """
        self.search([])._recycle_records(batch_commits=True)
        recycle_model_id = self.env.context.get('recycle_model_id')
        action = self.env["ir.actions.actions"]._for_xml_id("data_recycle.action_data_recycle_record")
        context = action.get('context', {})
        if isinstance(context, str):
            context = ast.literal_eval(context)
        if recycle_model_id:
            context['searchpanel_default_recycle_model_id'] = recycle_model_id
        action['context'] = context
        action['target'] = 'main'
        return action
