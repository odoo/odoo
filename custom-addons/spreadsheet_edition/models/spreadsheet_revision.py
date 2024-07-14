# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import api, fields, models


class SpreadsheetRevision(models.Model):
    _name = "spreadsheet.revision"
    _description = "Collaborative spreadsheet revision"
    _rec_name = 'revision_id'
    _rec_names_search = ['name', 'revision_id']

    name = fields.Char("Revision name")
    active = fields.Boolean(default=True)
    res_model = fields.Char(string="Model", required=True)
    res_id = fields.Many2oneReference(string="Record id", model_field='res_model', required=True)
    commands = fields.Char(required=True)
    revision_id = fields.Char(required=True)
    parent_revision_id = fields.Char(required=True)
    _sql_constraints = [
        ('parent_revision_unique', 'unique(parent_revision_id, res_id, res_model)', 'o-spreadsheet revision refused due to concurrency')
    ]

    @api.depends('name', 'revision_id')
    def _compute_display_name(self):
        for revision in self:
            revision.display_name = revision.name or revision.revision_id

    @api.autovacuum
    def _gc_revisions(self):
        """Delete the history for spreadsheets that have not been modified for more
        than a year (overridable with an 'ir.config_parameter').
        """
        inactivity_days = self.env['ir.config_parameter'].sudo().get_param(
            'spreadsheet_edition.gc_revisions_inactivity_in_days',
            '365'
        )
        one_year_ago = fields.Datetime.now() - relativedelta(days=int(inactivity_days))
        inactive_spreadsheets = self.with_context(active_test=False)._read_group(
            domain=[],
            groupby=["res_model", "res_id"],
            aggregates=["write_date:max"],
            having=[("write_date:max", "<=", one_year_ago)],
        )
        ids_by_model = defaultdict(list)
        for res_model, res_id, _last_revision_date in inactive_spreadsheets:
            ids_by_model[res_model].append(res_id)
        for res_model, res_ids in ids_by_model.items():
            records = self.env[res_model].browse(res_ids).with_context(preserve_spreadsheet_revisions=True)
            for record in records:
                # reset the initial data to the current snapshot
                record.spreadsheet_binary_data = record.spreadsheet_snapshot
            self.search([
                ("res_model", "=", res_model),
                ("res_id", "in", res_ids),
                ("active", "=", False),
            ]).unlink()
