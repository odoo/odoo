# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models, api, fields, _


class DataRecycleRecord(models.Model):
    _name = 'data_recycle.record'
    _description = 'Recycling Record'

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Record Name', compute='_compute_name', compute_sudo=True)
    recycle_model_id = fields.Many2one('data_recycle.model', string='Recycle Model', ondelete='cascade')

    res_id = fields.Integer('Record ID', index=True)
    res_model_id = fields.Many2one(related='recycle_model_id.res_model_id', store=True, readonly=True)
    res_model_name = fields.Char(related='recycle_model_id.res_model_name', store=True, readonly=True)

    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True)

    @api.model
    def _get_company_id(self, record):
        company_id = self.env['res.company']
        if 'company_id' in self.env[record._name]:
            company_id = record.company_id
        return company_id

    @api.depends('res_id')
    def _compute_name(self):
        original_records = {(r._name, r.id): r for r in self._original_records()}
        for record in self:
            original_record = original_records.get((record.res_model_name, record.res_id))
            if original_record:
                record.name = original_record.display_name or _('Undefined Name')
            else:
                record.name = _('**Record Deleted**')

    @api.depends('res_id')
    def _compute_company_id(self):
        original_records = {(r._name, r.id): r for r in self._original_records()}
        for record in self:
            original_record = original_records.get((record.res_model_name, record.res_id))
            if original_record:
                record.company_id = self._get_company_id(original_record)
            else:
                record.company_id = self.env['res.company']

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
        records_done = self.env['data_recycle.record']
        record_ids_to_archive = defaultdict(list)
        record_ids_to_unlink = defaultdict(list)
        original_records = {'%s_%s' % (r._name, r.id): r for r in self._original_records()}
        for record in self:
            original_record = original_records.get('%s_%s' % (record.res_model_name, record.res_id))
            records_done |= record
            if not original_record:
                continue
            if record.recycle_model_id.recycle_action == "archive":
                record_ids_to_archive[original_record._name].append(original_record.id)
            elif record.recycle_model_id.recycle_action == "unlink":
                record_ids_to_unlink[original_record._name].append(original_record.id)
        for model_name, ids in record_ids_to_archive.items():
            self.env[model_name].sudo().browse(ids).toggle_active()
        for model_name, ids in record_ids_to_unlink.items():
            self.env[model_name].sudo().browse(ids).unlink()
        records_done.unlink()

    def action_discard(self):
        self.write({'active': False})
