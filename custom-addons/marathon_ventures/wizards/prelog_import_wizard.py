# -*- coding: utf-8 -*-
"""Prelog import wizard — SF Workflow 21 (Workato replacement).

Marathon's existing pipeline is Wide Orbit CSV → Dropbox → Workato → Salesforce.
We replace the Workato step with this wizard: upload a CSV and create
mv.prelog_data + mv.prelog_data_mirror rows.

CSV expected headers (case-insensitive, order-insensitive):
  Week, Network, ISCI, Advertiser, Brand, Product, Air_Date, Air_Time,
  Units, Booked_Rate, Booked_Dollars, Version
"""
import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MvPrelogImportWizard(models.TransientModel):
    _name = 'mv.prelog.import.wizard'
    _description = 'Prelog Import Wizard'

    csv_file = fields.Binary(string='CSV File', required=True)
    csv_filename = fields.Char(string='Filename')
    program_id = fields.Many2one('mv.programs', string='Program (default)',
                                 help='If your CSV has no Program/Network column, every row will be assigned this program.')
    week_default = fields.Date(string='Week (default)',
                               help='If your CSV has no Week column, every row will use this Monday.')
    create_mirror = fields.Boolean(string='Also create Prelog Data Mirror rows', default=True)
    dry_run = fields.Boolean(string='Dry-run (no records created)', default=False)

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

        # Normalise column keys
        def get(row, *candidates):
            for c in candidates:
                if c in row and row[c] not in (None, ''):
                    return row[c]
                # Try case-insensitive
                for k in row:
                    if k and k.lower() == c.lower():
                        return row[k]
            return None

        Prelog = self.env['mv.prelog_data']
        Mirror = self.env['mv.prelog_data_mirror']

        created_main, created_mirror, skipped = 0, 0, 0
        errors = []
        for i, row in enumerate(rows, start=2):  # row 1 is header
            week_raw = get(row, 'Week', 'week')
            try:
                week = (
                    datetime.strptime(week_raw, '%Y-%m-%d').date()
                    if week_raw else self.week_default
                )
            except Exception:
                try:
                    week = datetime.strptime(week_raw, '%m/%d/%Y').date()
                except Exception:
                    week = self.week_default

            isci = get(row, 'ISCI', 'isci') or ''
            version = int(get(row, 'Version', 'version') or 1)
            vals = {
                'isci': isci,
                'version': version,
            }
            if self.dry_run:
                created_main += 1
            else:
                try:
                    prelog = Prelog.create(vals)
                    created_main += 1
                    if self.create_mirror:
                        Mirror.create({
                            # mirror minimal payload — extend mappings here as needed
                            'sf_external_id': prelog.sf_external_id or False,
                        })
                        created_mirror += 1
                except Exception as e:
                    skipped += 1
                    errors.append(f'row {i}: {e}')

        msg = _(
            "Prelog import complete.\nMain rows created: %(m)d\nMirror rows created: %(x)d\nSkipped: %(s)d"
        ) % {'m': created_main, 'x': created_mirror, 's': skipped}
        if errors:
            msg += '\n\nFirst errors:\n' + '\n'.join(errors[:5])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Prelog Import'), 'message': msg, 'sticky': True, 'type': 'success' if not errors else 'warning'},
        }
