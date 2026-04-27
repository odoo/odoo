# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.addons.phone_validation.tools.phone_validation import phone_format


class DataCleaningRecord(models.Model):
    _name = 'data_cleaning.record'
    _description = 'Cleaning Record'

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Record Name', compute='_compute_non_stored_values', compute_sudo=True)
    rule_ids = fields.Many2many('data_cleaning.rule', string='Rule', required=True, ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', string='Field')
    cleaning_model_id = fields.Many2one('data_cleaning.model', string='Cleaning Model', ondelete='cascade')
    field_name = fields.Char(related='field_id.name')
    action = fields.Char('Actions', compute='_compute_non_stored_values', compute_sudo=True)

    res_id = fields.Integer('Record ID', index=True)
    res_model_id = fields.Many2one(related='cleaning_model_id.res_model_id', store=True, readonly=True)
    res_model_name = fields.Char(related='cleaning_model_id.res_model_name', store=True, readonly=True)

    current_value = fields.Char('Current', compute='_compute_non_stored_values', compute_sudo=True)
    suggested_value = fields.Char('Suggested Value', compute='_compute_non_stored_values', compute_sudo=True)
    suggested_value_display = fields.Char('Suggested', compute='_compute_non_stored_values', compute_sudo=True)
    country_id = fields.Many2one('res.country', compute='_compute_stored_values', store=True)
    company_id = fields.Many2one('res.company', compute='_compute_stored_values', store=True)

    @api.model
    def _get_country_id(self, record):
        country_id = self.env['res.country']
        if 'country_id' in self.env[record._name] and record.country_id:
            country_id = record.country_id
        elif 'company_id' in self.env[record._name] and record.company_id.country_id:
            country_id = record.company_id.country_id
        return country_id

    @api.model
    def _get_company_id(self, record):
        company_id = self.env['res.company']
        if 'company_id' in self.env[record._name]:
            company_id = record.company_id
        return company_id

    def _render_value(self, current_value):
        self.ensure_one()

        def _render(record, value, methods):
            if methods and methods[0] is not None:
                return _render(record, methods[0](record, value), methods[1:])
            return (record, value)

        render = [rule_id._action_to_python() for rule_id in self.rule_ids.sorted(key=lambda r: r.sequence)]
        return _render(self, current_value, render)[1]

    @api.depends('res_id')
    def _compute_non_stored_values(self):
        original_records = {'%s_%s' % (r._name, r.id): r for r in self._original_records()}
        for record in self:
            original_record = original_records.get('%s_%s' % (record.res_model_name, record.res_id))
            if original_record:
                # update those values now as we might need them to render some actions (e.g. format_phone)
                current_value = original_record[record.field_name] or ''
                suggested_value = record._render_value(current_value)
                suggested_value_display = suggested_value
                if any(rule_id.action == 'trim' for rule_id in record.rule_ids):
                    # non-breaking space, to render multiple spaces in the backend
                    current_value = current_value.replace(' ', '\u00a0').replace('\t', '\u00a0')
                    suggested_value_display = suggested_value_display.replace(' ', '\u00a0').replace('\t', '\u00a0')
                record.name = original_record.display_name
                record.current_value = current_value
                record.action = ', '.join(record.rule_ids.mapped('action_display'))
                record.suggested_value = suggested_value
                record.suggested_value_display = suggested_value
            else:
                record.name = '**Record Deleted**'
                record.current_value = '**Record Deleted**'
                record.suggested_value = '**Record Deleted**'
                record.suggested_value_display = '**Record Deleted**'
                record.action = '**Record Deleted**'

    @api.depends('res_id')
    def _compute_stored_values(self):
        original_records = {'%s_%s' % (r._name, r.id): r for r in self._original_records()}
        for record in self:
            original_record = original_records.get('%s_%s' % (record.res_model_name, record.res_id))
            if original_record:
                record.country_id = self._get_country_id(original_record)
                record.company_id = self._get_company_id(original_record)
            else:
                record.country_id = False
                record.company_id = False

    def _original_records(self):
        if not self:
            return []

        records = []
        records_per_model = {}
        for record in self.filtered(lambda r: r.res_model_name):
            ids = records_per_model.get(record.res_model_name, [])
            ids.append(record.res_id)
            records_per_model[record.res_model_name] = ids

        for model, record_ids in records_per_model.items():
            recs = self.env[model].with_context(active_test=False).sudo().browse(record_ids).exists()
            records += [r for r in recs]
        return records

    def action_validate(self):
        records_done = self.env['data_cleaning.record']
        original_records = {'%s_%s' % (r._name, r.id): r for r in self._original_records()}
        for record in self:
            original_record = original_records.get('%s_%s' % (record.res_model_name, record.res_id))
            records_done |= record
            if not original_record:
                continue
            field_name = record.field_name
            original_record[0].update({
                field_name: record.suggested_value
            })
        records_done.unlink()

    def action_discard(self):
        self.write({'active': False})
