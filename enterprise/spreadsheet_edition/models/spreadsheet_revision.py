# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import SQL


class SpreadsheetRevision(models.Model):
    _name = "spreadsheet.revision"
    _description = "Collaborative spreadsheet revision"
    _rec_name = 'revision_uuid'
    _rec_names_search = ['name', 'revision_uuid']

    name = fields.Char("Revision name")
    active = fields.Boolean(default=True)
    res_model = fields.Char(string="Model", required=True)
    res_id = fields.Many2oneReference(string="Record id", model_field='res_model', required=True)
    commands = fields.Char(required=True)
    revision_uuid = fields.Char(required=True, index=True)
    parent_revision_id = fields.Many2one("spreadsheet.revision", copy=False)

    # virtual constraints implemented by a custom index below
    _sql_constraints = [
        ('initial_unique', '', "There can be only one initial revision per spreadsheet"),
        ('parent_unique', '', "A revision based on the same revision already exists"),
    ]

    def init(self):
        self.env.cr.execute(
            SQL(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS spreadsheet_revision_initial_unique
                ON %s (res_model, res_id) WHERE parent_revision_id IS NULL
                """,
                SQL.identifier(self._table)
            )
        )
        self.env.cr.execute(
            SQL(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS spreadsheet_revision_parent_unique
                ON %s (parent_revision_id, res_model, res_id) WHERE parent_revision_id IS NOT NULL
                """,
                SQL.identifier(self._table)
            )
        )

    @api.depends('name', 'revision_uuid')
    def _compute_display_name(self):
        for revision in self:
            revision.display_name = revision.name or revision.revision_uuid

    @api.autovacuum
    def _gc_revisions(self, domain=(), inactivity_days=365):
        """Delete the history for spreadsheets that have not been modified for more
        than a year (overridable with an 'ir.config_parameter').
        """
        config_param = self.env['ir.config_parameter'].sudo().get_param(
            'spreadsheet_edition.gc_revisions_inactivity_in_days',
            ''
        )
        if config_param:
            inactivity_days = int(config_param)
        one_year_ago = fields.Datetime.now() - relativedelta(days=inactivity_days)
        inactive_spreadsheets = self.with_context(active_test=False)._read_group(
            domain=domain,
            groupby=["res_model", "res_id"],
            aggregates=["write_date:max"],
            having=[("write_date:max", "<=", one_year_ago)],
        )
        ids_by_model = defaultdict(list)
        for res_model, res_id, _last_revision_date in inactive_spreadsheets:
            ids_by_model[res_model].append(res_id)
        for res_model, res_ids in ids_by_model.items():
            records = self.env[res_model].browse(res_ids).with_context(preserve_spreadsheet_revisions=True)
            for record in records.filtered('spreadsheet_snapshot'):
                # reset the initial data to the current snapshot
                record.spreadsheet_binary_data = record.spreadsheet_snapshot
            self.search([
                ("res_model", "=", res_model),
                ("res_id", "in", res_ids),
                ("active", "=", False),
            ]).unlink()
