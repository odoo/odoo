# -*- coding: utf-8 -*-
"""Postlog import wizard — SF Workflow 22 (Workato replacement).

Upload a Wide Orbit postlog CSV → create mv.spot_data + mv.spot_data_mirror rows.

CSV expected headers (case-insensitive):
  Week, Network, ISCI, Air_Date, Air_Time, Units, Rate, Total_Dollars
"""
import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MvPostlogImportWizard(models.TransientModel):
    _name = 'mv.postlog.import.wizard'
    _description = 'Postlog Import Wizard'

    csv_file = fields.Binary(string='CSV File', required=True)
    csv_filename = fields.Char(string='Filename')
    program_id = fields.Many2one('mv.programs', string='Program (default)')
    week_default = fields.Date(string='Week (default)')
    create_mirror = fields.Boolean(string='Also create Spot Data Mirror rows', default=True)
    dry_run = fields.Boolean(string='Dry-run', default=False)

    def action_import(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_("Pick a CSV file first."))
        try:
            raw = base64.b64decode(self.csv_file).decode('utf-8-sig', errors='replace')
        except Exception as e:
            raise UserError(_("Could not decode the file as UTF-8 CSV: %s") % e) from e

        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        if not rows:
            raise UserError(_("The CSV is empty (no data rows)."))

        SpotData = self.env['mv.spot_data']
        SpotMirror = self.env['mv.spot_data_mirror']

        def get(row, *candidates):
            for c in candidates:
                if c in row and row[c] not in (None, ''):
                    return row[c]
                for k in row:
                    if k and k.lower() == c.lower():
                        return row[k]
            return None

        created_main, created_mirror, skipped = 0, 0, 0
        errors = []
        for i, row in enumerate(rows, start=2):
            isci = get(row, 'ISCI', 'isci') or ''
            air_time = get(row, 'Air_Time', 'air_time') or ''
            vals = {
                'isci': isci,
            }
            if self.dry_run:
                created_main += 1
                continue
            try:
                sd = SpotData.create(vals)
                created_main += 1
                if self.create_mirror:
                    SpotMirror.create({
                        'isci': isci,
                        'air_time': air_time,
                        'status': 'aired',
                    })
                    created_mirror += 1
            except Exception as e:
                skipped += 1
                errors.append(f'row {i}: {e}')

        msg = _(
            "Postlog import complete.\nSpot Data rows: %(m)d\nMirror rows: %(x)d\nSkipped: %(s)d"
        ) % {'m': created_main, 'x': created_mirror, 's': skipped}
        if errors:
            msg += '\n\nFirst errors:\n' + '\n'.join(errors[:5])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Postlog Import'), 'message': msg, 'sticky': True, 'type': 'success' if not errors else 'warning'},
        }
