# -*- coding: utf-8 -*-
"""Phase 17 - Data Loader (Salesforce-style Import/Export framework).

Generic framework for importing and exporting any Odoo model's data
via CSV. Modes:

    * insert : create new records
    * update : write existing records matched by a key field
    * upsert : update if match found, else create
    * delete : unlink records matched by a key field
    * export : dump records selected by domain to a downloadable CSV

Workflow (import modes):

    draft -> mapped -> previewed -> running -> done | failed

Row-level results and errors are logged to mv.dataloader.line so the
user can drill into any failure. A CSV of errors-only is generated
at end-of-run for download.

Scope for this MVP: features 1-13 + 15 from the spec. Deliberately
does NOT include background jobs, scheduling, templates, rollback,
duplicate-detection modes, or bus-notification progress bars.
Those can be layered on later without changing the core schema.
"""
import base64
import csv
import io
import json
import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Field types where we accept "resolve by X" semantics for imports.
_RELATIONAL_TYPES = ('many2one', 'one2many', 'many2many')
_SCALAR_TYPES = (
    'char', 'text', 'html', 'integer', 'float', 'monetary',
    'boolean', 'date', 'datetime', 'selection', 'binary',
)

_BOOLEAN_TRUE = {'1', 'true', 'yes', 'y', 't'}
_BOOLEAN_FALSE = {'0', 'false', 'no', 'n', 'f', ''}


# =====================================================================
# mv.dataloader.job
# =====================================================================
class MvDataloaderJob(models.Model):
    _name = 'mv.dataloader.job'
    _description = 'Data Loader Job'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Job Name', default='New', copy=False, required=True,
    )
    mode = fields.Selection([
        ('insert', 'Insert (create new)'),
        ('update', 'Update (match + write)'),
        ('upsert', 'Upsert (update or create)'),
        ('delete', 'Delete (match + unlink)'),
        ('export', 'Export (download CSV)'),
    ], string='Mode', required=True, default='insert', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('mapped', 'Mapped'),
        ('previewed', 'Previewed'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True, copy=False)

    # NOTE: model_id is NOT required at the DB level so the
    # wizard can persist a draft on Step 1 (mode) before the
    # user has picked a model on Step 2. Actual validation
    # happens at each state transition (action_load_and_automap,
    # action_preview, action_execute), which fail loudly if the
    # model is still blank.
    model_id = fields.Many2one(
        'ir.model', string='Target Model',
        ondelete='cascade', tracking=True,
    )
    model_name = fields.Char(related='model_id.model', store=True, readonly=True)

    # Uploaded source file (import modes only)
    source_file = fields.Binary(string='CSV File', attachment=True, copy=False)
    source_filename = fields.Char(string='Filename', copy=False)
    header_row = fields.Boolean(
        string='First Row Is Header', default=True,
        help='Uncheck if your CSV has no header row.',
    )
    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)'),
    ], default=',', string='Delimiter')

    # Match-key field for update / upsert / delete
    match_field_id = fields.Many2one(
        'ir.model.fields', string='Match Field',
        domain="[('model_id', '=', model_id), ('store', '=', True)]",
        help='Field used to find existing records for update/upsert/delete. '
             'Leave blank on Insert.',
    )
    # Use id / external id / value comparison for the match
    match_by = fields.Selection([
        ('id', 'Odoo ID (integer)'),
        ('external_id', 'External ID (module.xmlid)'),
        ('value', 'Field value (exact match)'),
    ], default='value', string='Match By')

    # If a row errors: keep going (skip) or halt the whole job.
    on_error = fields.Selection([
        ('skip', 'Skip row, continue'),
        ('stop', 'Stop the whole job'),
    ], default='skip', string='On Error')

    # Relationships
    mapping_ids = fields.One2many(
        'mv.dataloader.mapping', 'job_id', string='Column Mapping', copy=True,
    )
    line_ids = fields.One2many(
        'mv.dataloader.line', 'job_id', string='Row Results', copy=False,
    )

    # --- Export-mode inputs ------------------------------------------
    export_field_ids = fields.Many2many(
        'ir.model.fields', 'mv_dl_job_export_field_rel', 'job_id', 'field_id',
        string='Export Fields',
        domain="[('model_id', '=', model_id), ('store', '=', True)]",
    )
    export_domain = fields.Char(
        string='Filter Domain', default='[]',
        help='Standard Odoo domain, e.g. [("active","=",True)].',
    )
    exported_file = fields.Binary(
        string='Exported CSV', attachment=True, readonly=True, copy=False,
    )
    exported_filename = fields.Char(string='Export Filename', readonly=True, copy=False)

    # --- Stats -------------------------------------------------------
    total_rows = fields.Integer(readonly=True, copy=False)
    success_count = fields.Integer(readonly=True, copy=False)
    error_count = fields.Integer(readonly=True, copy=False)
    skip_count = fields.Integer(readonly=True, copy=False)
    started_at = fields.Datetime(readonly=True, copy=False)
    finished_at = fields.Datetime(readonly=True, copy=False)
    duration_seconds = fields.Float(
        compute='_compute_duration', store=True,
        string='Duration (s)', readonly=True,
    )
    error_report = fields.Binary(
        string='Error Report (CSV)', readonly=True, copy=False,
        attachment=True,
    )
    error_report_filename = fields.Char(readonly=True, copy=False)

    user_id = fields.Many2one(
        'res.users', string='Executed By',
        default=lambda self: self.env.user,
    )

    # ================================================================
    # Housekeeping
    # ================================================================
    @api.depends('started_at', 'finished_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.finished_at:
                delta = rec.finished_at - rec.started_at
                rec.duration_seconds = delta.total_seconds()
            else:
                rec.duration_seconds = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self._next_job_name(vals.get('mode', 'insert'))
        return super().create(vals_list)

    def _next_job_name(self, mode):
        prefix = {
            'insert': 'IMP',   'update': 'UPD',
            'upsert': 'UPS',   'delete': 'DEL',
            'export': 'EXP',
        }.get(mode, 'JOB')
        stamp = fields.Datetime.now().strftime('%Y%m%d-%H%M%S')
        return '%s/%s' % (prefix, stamp)

    @api.onchange('model_id')
    def _onchange_model_reset(self):
        # Model swap invalidates existing column mappings + export fields.
        self.mapping_ids = [(5, 0, 0)]
        self.export_field_ids = [(5, 0, 0)]
        self.match_field_id = False

    # ================================================================
    # File parsing
    # ================================================================
    def _read_csv_rows(self):
        """Return (header, rows) tuple. header is [] if header_row=False.
        Rows is a list of list[str]. Raises UserError on parse issues.

        Handles both CSV and Excel (.xlsx) uploads - dispatched by
        the source filename extension. Legacy .xls (BIFF binary
        format) is NOT supported; users must save as .xlsx or .csv.
        """
        self.ensure_one()
        if not self.source_file:
            raise UserError(_('No file uploaded.'))
        try:
            raw = base64.b64decode(self.source_file)
        except Exception as e:
            raise UserError(_('Cannot decode file: %s') % e)
        fname = (self.source_filename or '').lower()
        if fname.endswith('.xlsx'):
            return self._read_xlsx_rows(raw)
        if fname.endswith('.xls'):
            raise UserError(_(
                'Legacy .xls files are not supported. Please save the '
                'workbook as .xlsx or .csv and try again.'
            ))
        # BOM sniff for UTF-16 first (Excel "Save As CSV UTF-16" or
        # PowerShell's default Out-File). UTF-16 stores ASCII as
        # alternating bytes with 0x00, which if decoded as UTF-8
        # gives strings full of NUL characters that Postgres rejects.
        text = None
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            try:
                text = raw.decode('utf-16')
            except UnicodeDecodeError:
                text = None
        # Otherwise: utf-8 with BOM stripping, fall back to latin-1
        if text is None:
            for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    text = None
        if text is None:
            raise UserError(_('Cannot decode CSV as utf-16, utf-8, or latin-1.'))
        # Belt-and-braces: strip any residual NUL characters. Postgres
        # rejects NUL in text columns, and even a valid-looking utf-8
        # file can contain accidental NULs from bad tooling.
        if '\x00' in text:
            text = text.replace('\x00', '')
        # newline='' tells StringIO not to translate line endings
        # (\r, \n, \r\n) - csv.reader needs the raw newlines to
        # correctly parse rows that contain quoted multi-line fields
        # or files saved with CRLF endings.
        reader = csv.reader(
            io.StringIO(text, newline=''), delimiter=self.delimiter or ',',
        )
        rows = [r for r in reader if any((c or '').strip() for c in r)]
        header = []
        if self.header_row and rows:
            header = [(h or '').strip() for h in rows[0]]
            rows = rows[1:]
        return header, rows

    def _read_xlsx_rows(self, raw):
        """Parse an .xlsx workbook and return (header, rows) using
        the same shape as _read_csv_rows(): header is [] when the
        job's header_row flag is off, rows is list[list[str]].
        Reads the first (active) worksheet only.

        Uses openpyxl, which is already a hard dependency of Odoo
        so no extra install is needed. data_only=True returns the
        last-computed value for formula cells; read_only=True
        streams cells for lower memory on big files.
        """
        try:
            import openpyxl
        except ImportError:
            raise UserError(_(
                'Reading .xlsx files requires the openpyxl library '
                '(usually bundled with Odoo). Please contact your '
                'administrator.'
            ))
        try:
            wb = openpyxl.load_workbook(
                io.BytesIO(raw), read_only=True, data_only=True,
            )
        except Exception as e:
            raise UserError(_('Cannot read .xlsx file: %s') % e)
        try:
            ws = wb.active
            if ws is None:
                raise UserError(_('The .xlsx file has no active worksheet.'))
            rows = []
            for wrow in ws.iter_rows(values_only=True):
                if wrow is None:
                    continue
                cells = [self._xlsx_cell_to_str(c) for c in wrow]
                if any((c or '').strip() for c in cells):
                    rows.append(cells)
            header = []
            if self.header_row and rows:
                header = [(h or '').strip() for h in rows[0]]
                rows = rows[1:]
            return header, rows
        finally:
            wb.close()

    @staticmethod
    def _xlsx_cell_to_str(v):
        """Turn any openpyxl cell value into a plain string for
        the mapping pipeline (which expects str rows just like the
        CSV path). Preserves numbers/dates in a lossless-ish form.
        """
        if v is None:
            return ''
        if isinstance(v, bool):
            return '1' if v else '0'
        if isinstance(v, (int, float)):
            # Trim trailing .0 on whole floats so integer-looking
            # numbers land in Integer fields cleanly.
            if isinstance(v, float) and v.is_integer():
                return str(int(v))
            return str(v)
        try:
            # datetime / date have .isoformat()
            return v.isoformat()
        except AttributeError:
            return str(v)

    # ================================================================
    # Auto-mapping
    # ================================================================
    def action_load_and_automap(self):
        """Parse the CSV header, drop any existing mapping, create one
        mv.dataloader.mapping per column. Try to auto-match each
        column to a field on the target model by name (case-insensitive
        + snake_case)."""
        if not self.model_id:
            raise UserError(_('Pick a target model first.'))
        for job in self:
            if job.mode == 'export':
                raise UserError(_(
                    'Auto-mapping is for import modes. Export uses the '
                    '"Export Fields" many2many below instead.'
                ))
            header, _rows = job._read_csv_rows()
            if not header:
                # Generate placeholder headers if user unchecked
                # "First row is header" (Column 1, Column 2, ...).
                if _rows:
                    header = ['Column %d' % (i + 1) for i in range(len(_rows[0]))]
                else:
                    raise UserError(_('CSV appears to be empty.'))
            job.mapping_ids.unlink()
            fields_by_name = {
                f.name: f for f in job._all_target_fields()
            }
            # Also index by lowercased label + snake_case column
            fields_by_label = {}
            for f in fields_by_name.values():
                if f.field_description:
                    fields_by_label.setdefault(
                        f.field_description.strip().lower(), f,
                    )
            new_lines = []
            for i, col in enumerate(header):
                guess = _guess_field(col, fields_by_name, fields_by_label)
                new_lines.append((0, 0, {
                    'sequence': i * 10,
                    'source_column': col,
                    'target_field_id': guess.id if guess else False,
                    'skip': False if guess else True,
                }))
            job.mapping_ids = new_lines
            if job.state == 'draft':
                job.state = 'mapped'
            job.message_post(body=_(
                'Loaded %(cols)d columns from <b>%(file)s</b>. Auto-mapped '
                '%(hits)d of %(cols)d.',
            ) % {
                'cols': len(header),
                'file': job.source_filename or 'file',
                'hits': sum(1 for m in job.mapping_ids if m.target_field_id),
            })
        return True

    def _all_target_fields(self):
        self.ensure_one()
        return self.env['ir.model.fields'].search([
            ('model_id', '=', self.model_id.id),
            ('store', '=', True),
        ])

    # ================================================================
    # Preview (validate first N rows)
    # ================================================================
    def action_preview(self, limit=25):
        for job in self:
            if job.mode == 'export':
                raise UserError(_(
                    'Preview is for import modes. For Export, use "Run Export" directly.'
                ))
            header, rows = job._read_csv_rows()
            job.line_ids.filtered(lambda l: l.status == 'preview').unlink()
            preview_rows = rows[:limit]
            job._create_preview_lines(header, preview_rows)
            if job.state in ('draft', 'mapped'):
                job.state = 'previewed'
        return True

    def _create_preview_lines(self, header, rows):
        self.ensure_one()
        Line = self.env['mv.dataloader.line']
        mapping_by_col = {
            m.source_column: m for m in self.mapping_ids if not m.skip
        }
        vals_list = []
        for row_i, row in enumerate(rows, start=1):
            try:
                vals_dict = self._row_to_vals(header, row, mapping_by_col)
                vals_list.append({
                    'job_id': self.id,
                    'row_number': row_i,
                    'status': 'preview',
                    'message': _('Validated. %d fields.') % len(vals_dict),
                    'payload': json.dumps(vals_dict, default=str),
                })
            except _ValidationError as e:
                vals_list.append({
                    'job_id': self.id,
                    'row_number': row_i,
                    'status': 'error',
                    'message': str(e),
                    'payload': json.dumps(dict(zip(header, row))),
                })
        if vals_list:
            Line.create(vals_list)

    # ================================================================
    # Row -> vals conversion + validation
    # ================================================================
    def _row_to_vals(self, header, row, mapping_by_col):
        """Turn one CSV row into an Odoo vals dict per the mapping.
        Raises _ValidationError on any issue."""
        vals = {}
        # Support both header-based and positional access.
        idx_by_col = {h: i for i, h in enumerate(header)}
        for col, m in mapping_by_col.items():
            f = m.target_field_id
            if not f:
                continue
            i = idx_by_col.get(col)
            if i is None or i >= len(row):
                raw = ''
            else:
                raw = (row[i] or '').strip()
            if raw == '' and f.required:
                raise _ValidationError(
                    _('Required field "%s" is empty.') % f.name,
                )
            if raw == '':
                continue
            vals[f.name] = self._coerce_value(f, m, raw)
        return vals

    def _coerce_value(self, ir_field, mapping, raw):
        """Cast the raw CSV string to a Python value fit for write/create."""
        ftype = ir_field.ttype
        if ftype in ('char', 'text', 'html'):
            return raw
        if ftype == 'integer':
            try:
                return int(raw)
            except ValueError:
                raise _ValidationError(
                    _('%s: expected integer, got %r') % (ir_field.name, raw),
                )
        if ftype in ('float', 'monetary'):
            try:
                return float(raw)
            except ValueError:
                raise _ValidationError(
                    _('%s: expected number, got %r') % (ir_field.name, raw),
                )
        if ftype == 'boolean':
            low = raw.lower()
            if low in _BOOLEAN_TRUE:
                return True
            if low in _BOOLEAN_FALSE:
                return False
            raise _ValidationError(
                _('%s: expected boolean, got %r') % (ir_field.name, raw),
            )
        if ftype == 'date':
            try:
                return fields.Date.from_string(raw)
            except Exception:
                raise _ValidationError(
                    _('%s: invalid date %r (expected YYYY-MM-DD)') % (ir_field.name, raw),
                )
        if ftype == 'datetime':
            try:
                return fields.Datetime.from_string(raw)
            except Exception:
                raise _ValidationError(
                    _('%s: invalid datetime %r') % (ir_field.name, raw),
                )
        if ftype == 'selection':
            # ir.model.fields exposes the selection via .selection_ids
            # OR via the model's field spec. Use the model's field
            # spec (authoritative + faster).
            Model = self.env[self.model_id.model]
            valid = dict(Model.fields_get([ir_field.name])[ir_field.name].get('selection') or [])
            if raw in valid:
                return raw
            # Also accept the label (human-facing string)
            for k, label in valid.items():
                if label == raw:
                    return k
            raise _ValidationError(
                _('%s: invalid selection %r. Valid: %s') % (
                    ir_field.name, raw, ', '.join(valid.keys()) or '(none)',
                ),
            )
        if ftype == 'many2one':
            return self._resolve_m2o(ir_field, mapping, raw)
        if ftype in ('one2many', 'many2many'):
            # Accept comma-separated list of ids/xmlids/values, resolve each
            parts = [p.strip() for p in raw.split(',') if p.strip()]
            ids = [self._resolve_m2o(ir_field, mapping, p) for p in parts]
            return [(6, 0, ids)]
        # Unknown scalar - pass through raw
        return raw

    def _resolve_m2o(self, ir_field, mapping, raw):
        """Resolve a many2one / m2m ref. mapping.match_key_for_m2o
        picks the lookup style ('id' / 'external_id' / a field name)."""
        Comodel = self.env[ir_field.relation]
        style = (mapping.match_key_for_m2o or 'name').strip()
        if style == 'id':
            try:
                rid = int(raw)
            except ValueError:
                raise _ValidationError(
                    _('%s: expected integer id, got %r') % (ir_field.name, raw),
                )
            if not Comodel.browse(rid).exists():
                raise _ValidationError(
                    _('%s: %s with id=%s not found.') % (
                        ir_field.name, ir_field.relation, rid,
                    ),
                )
            return rid
        if style == 'external_id':
            rec = self.env.ref(raw, raise_if_not_found=False)
            if not rec or rec._name != ir_field.relation:
                raise _ValidationError(
                    _('%s: external id %r not found on %s.') % (
                        ir_field.name, raw, ir_field.relation,
                    ),
                )
            return rec.id
        # Field-name lookup
        found = Comodel.search([(style, '=', raw)], limit=2)
        if not found:
            raise _ValidationError(
                _('%s: %s with %s=%r not found.') % (
                    ir_field.name, ir_field.relation, style, raw,
                ),
            )
        if len(found) > 1:
            raise _ValidationError(
                _('%s: %s with %s=%r is ambiguous (%d matches).') % (
                    ir_field.name, ir_field.relation, style, raw, len(found),
                ),
            )
        return found.id

    # ================================================================
    # Execute
    # ================================================================
    def action_execute(self):
        for job in self:
            if not job.model_id:
                raise UserError(_('Pick a target model before running the job.'))
            if job.mode == 'export':
                job._do_export()
            else:
                job._do_import()
        return True

    def _do_import(self):
        self.ensure_one()
        if self.mode in ('update', 'upsert', 'delete') and not self.match_field_id:
            raise UserError(_(
                'Mode "%s" requires a Match Field.',
            ) % self.mode)
        header, rows = self._read_csv_rows()
        # Wipe any preview lines - they'll be regenerated with real status
        self.line_ids.unlink()
        Line = self.env['mv.dataloader.line']
        mapping_by_col = {
            m.source_column: m for m in self.mapping_ids if not m.skip
        }
        self.write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'total_rows': len(rows),
            'success_count': 0,
            'error_count': 0,
            'skip_count': 0,
            'error_report': False,
            'error_report_filename': False,
        })
        self.env.cr.commit()   # persist start state before batching

        Target = self.env[self.model_id.model]
        idx_by_col = {h: i for i, h in enumerate(header)}
        # For update / upsert / delete we look up existing rec per row.
        # Match-field name resolved once for speed.
        match_col = None
        if self.match_field_id:
            for col, m in mapping_by_col.items():
                if m.target_field_id.id == self.match_field_id.id:
                    match_col = col
                    break
        try:
            success = errors = skipped = 0
            line_batch = []
            for row_i, row in enumerate(rows, start=1):
                status, res_id, message = self._process_row(
                    Target, header, row, mapping_by_col, idx_by_col, match_col,
                )
                if status == 'error':
                    errors += 1
                    if self.on_error == 'stop':
                        line_batch.append({
                            'job_id': self.id, 'row_number': row_i,
                            'status': 'error', 'res_id': 0,
                            'message': message,
                            'payload': json.dumps(dict(zip(header, row))),
                        })
                        Line.create(line_batch)
                        self.write({
                            'state': 'failed',
                            'finished_at': fields.Datetime.now(),
                            'success_count': success, 'error_count': errors,
                            'skip_count': skipped,
                        })
                        self._render_error_report()
                        self._send_completion_email()
                        return
                elif status == 'skipped':
                    skipped += 1
                else:
                    success += 1
                line_batch.append({
                    'job_id': self.id,
                    'row_number': row_i,
                    'status': status,
                    'res_id': res_id or 0,
                    'message': message,
                    'payload': json.dumps(dict(zip(header, row))),
                })

            if line_batch:
                Line.create(line_batch)
            self.write({
                'state': 'done',
                'finished_at': fields.Datetime.now(),
                'success_count': success,
                'error_count': errors,
                'skip_count': skipped,
            })
            self._render_error_report()
            self.message_post(body=_(
                'Import finished: %(s)d ok, %(e)d errors, %(k)d skipped.',
            ) % {'s': success, 'e': errors, 'k': skipped})
            self._send_completion_email()
        except Exception as e:
            _logger.exception('Data loader job %s failed', self.name)
            self.env.cr.rollback()
            self.write({
                'state': 'failed', 'finished_at': fields.Datetime.now(),
            })
            self.message_post(body=_(
                'Import failed: %s',
            ) % e)
            self._send_completion_email()

    def _process_row(self, Target, header, row, mapping_by_col, idx_by_col, match_col):
        """Returns (status, res_id, message). status is
        'created' | 'updated' | 'skipped' | 'error'."""
        try:
            vals = self._row_to_vals(header, row, mapping_by_col)
        except _ValidationError as e:
            return 'error', 0, str(e)
        if self.mode == 'insert':
            try:
                rec = Target.create(vals)
                return 'created', rec.id, _('Created id=%d') % rec.id
            except Exception as e:
                return 'error', 0, _('create() failed: %s') % e
        # update / upsert / delete need a match value
        raw_match = ''
        if match_col is not None:
            i = idx_by_col.get(match_col)
            if i is not None and i < len(row):
                raw_match = (row[i] or '').strip()
        if not raw_match:
            return 'error', 0, _('Match field %s is empty.') % (
                self.match_field_id.name if self.match_field_id else '?',
            )
        existing = self._find_existing(Target, raw_match)
        if self.mode == 'update':
            if not existing:
                return 'error', 0, _('No record matched %s=%r') % (
                    self.match_field_id.name, raw_match,
                )
            if len(existing) > 1:
                return 'error', 0, _('Ambiguous match: %d records for %s=%r') % (
                    len(existing), self.match_field_id.name, raw_match,
                )
            try:
                existing.write(vals)
                return 'updated', existing.id, _('Updated id=%d') % existing.id
            except Exception as e:
                return 'error', 0, _('write() failed: %s') % e
        if self.mode == 'upsert':
            if existing and len(existing) == 1:
                try:
                    existing.write(vals)
                    return 'updated', existing.id, _('Updated id=%d') % existing.id
                except Exception as e:
                    return 'error', 0, _('write() failed: %s') % e
            if existing and len(existing) > 1:
                return 'error', 0, _('Ambiguous match: %d records for %s=%r') % (
                    len(existing), self.match_field_id.name, raw_match,
                )
            try:
                rec = Target.create(vals)
                return 'created', rec.id, _('Created id=%d') % rec.id
            except Exception as e:
                return 'error', 0, _('create() failed: %s') % e
        if self.mode == 'delete':
            if not existing:
                return 'skipped', 0, _('No record matched %s=%r') % (
                    self.match_field_id.name, raw_match,
                )
            try:
                deleted_ids = existing.ids
                existing.unlink()
                return ('updated' if False else 'deleted'), 0, _(
                    'Deleted ids=%s',
                ) % deleted_ids
            except Exception as e:
                return 'error', 0, _('unlink() failed: %s') % e
        return 'error', 0, _('Unknown mode: %s') % self.mode

    def _find_existing(self, Target, raw_match):
        """Look up existing record(s) by the configured match key."""
        if self.match_by == 'id':
            try:
                rid = int(raw_match)
            except ValueError:
                return Target.browse([])
            rec = Target.browse(rid)
            return rec if rec.exists() else Target.browse([])
        if self.match_by == 'external_id':
            rec = self.env.ref(raw_match, raise_if_not_found=False)
            if rec and rec._name == Target._name:
                return rec
            return Target.browse([])
        # 'value' - use the match_field as a field-value lookup
        fname = self.match_field_id.name
        return Target.search([(fname, '=', raw_match)])

    # ================================================================
    # Export
    # ================================================================
    def _do_export(self):
        self.ensure_one()
        Target = self.env[self.model_id.model]
        # Parse the domain
        try:
            dom = eval(self.export_domain or '[]', {'__builtins__': {}}, {})  # noqa: S307
        except Exception as e:
            raise UserError(_('Invalid export domain: %s') % e)
        fnames = [f.name for f in self.export_field_ids] or ['id']
        self.write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
        })
        try:
            recs = Target.search(dom)
            data = recs.read(fnames)
            buf = io.StringIO()
            writer = csv.writer(buf, delimiter=self.delimiter or ',')
            writer.writerow(fnames)
            for row in data:
                writer.writerow([_flatten_cell(row.get(f)) for f in fnames])
            payload = buf.getvalue().encode('utf-8')
            fname = '%s_%s.csv' % (
                self.model_name.replace('.', '_'),
                fields.Datetime.now().strftime('%Y%m%d-%H%M%S'),
            )
            self.write({
                'state': 'done',
                'finished_at': fields.Datetime.now(),
                'total_rows': len(recs),
                'success_count': len(recs),
                'exported_file': base64.b64encode(payload),
                'exported_filename': fname,
            })
            self.message_post(body=_(
                'Exported %d records to <b>%s</b>.',
            ) % (len(recs), fname))
            self._send_completion_email()
        except Exception as e:
            _logger.exception('Export job %s failed', self.name)
            self.env.cr.rollback()
            self.write({
                'state': 'failed', 'finished_at': fields.Datetime.now(),
            })
            self.message_post(body=_('Export failed: %s') % e)
            self._send_completion_email()

    # ================================================================
    # Completion email
    # ================================================================
    def _send_completion_email(self):
        """Email the job owner (user_id) once the job has finished.
        Attaches:
          * the original uploaded source file (CSV / xlsx)
          * the error-report CSV (if any errors were recorded)
          * the exported file (for export-mode jobs)

        Body includes a row-level breakdown with status + message.
        Skips silently if the user has no email address configured.
        """
        self.ensure_one()
        user = self.user_id or self.env.user
        if not user or not user.email:
            _logger.info(
                '[MV Data Loader] Skipping completion email for job %s: '
                'user %s has no email address.',
                self.name, user.login if user else '(none)',
            )
            return
        Attachment = self.env['ir.attachment']
        attachment_ids = []
        # 1) Original source file
        if self.source_file:
            att = Attachment.create({
                'name': self.source_filename or 'source.csv',
                'datas': self.source_file,
                'res_model': 'mv.dataloader.job',
                'res_id': self.id,
            })
            attachment_ids.append(att.id)
        # 2) Error report CSV
        if self.error_report:
            att = Attachment.create({
                'name': self.error_report_filename or 'errors.csv',
                'datas': self.error_report,
                'res_model': 'mv.dataloader.job',
                'res_id': self.id,
            })
            attachment_ids.append(att.id)
        # 3) Exported CSV (export-mode only)
        if self.exported_file:
            att = Attachment.create({
                'name': self.exported_filename or 'export.csv',
                'datas': self.exported_file,
                'res_model': 'mv.dataloader.job',
                'res_id': self.id,
            })
            attachment_ids.append(att.id)
        body = self._render_completion_html()
        subject = '[Data Loader] %s - %s' % (
            self.name or 'Job', (self.state or '').title() or 'Completed',
        )
        Mail = self.env['mail.mail']
        mail = Mail.sudo().create({
            'subject': subject,
            'body_html': body,
            'email_to': user.email,
            'email_from': (
                self.env.user.email_formatted
                or self.env.company.email
                or None
            ),
            'attachment_ids': [(6, 0, attachment_ids)],
        })
        try:
            mail.send()
        except Exception as e:
            _logger.exception(
                '[MV Data Loader] Completion email failed for job %s: %s',
                self.name, e,
            )

    def _render_completion_html(self):
        """Return the HTML body of the completion email.
        Caps the per-row table at 500 rows to keep messages sane;
        the full error listing is in the attached error CSV.
        """
        self.ensure_one()
        deal_summary = (
            '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;margin-bottom:16px;">'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Job</td><td style="padding:4px 0;"><b>%(name)s</b></td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Mode</td><td style="padding:4px 0;">%(mode)s</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Model</td><td style="padding:4px 0;">%(model)s</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Status</td><td style="padding:4px 0;"><b style="color:%(state_color)s;">%(state)s</b></td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Source file</td><td style="padding:4px 0;">%(filename)s</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Started</td><td style="padding:4px 0;">%(started)s</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Finished</td><td style="padding:4px 0;">%(finished)s</td></tr>'
            '<tr><td style="padding:4px 12px 4px 0;color:#666;">Duration</td><td style="padding:4px 0;">%(duration).2f s</td></tr>'
            '</table>'
        ) % {
            'name': self.name or '',
            'mode': dict(self._fields['mode'].selection).get(self.mode, self.mode or ''),
            'model': (self.model_id.name or self.model_name or ''),
            'state': (self.state or '').title(),
            'state_color': '#198754' if self.state == 'done' else '#dc3545' if self.state == 'failed' else '#6c757d',
            'filename': self.source_filename or self.exported_filename or '-',
            'started': self.started_at.isoformat(sep=' ', timespec='seconds') if self.started_at else '-',
            'finished': self.finished_at.isoformat(sep=' ', timespec='seconds') if self.finished_at else '-',
            'duration': self.duration_seconds or 0.0,
        }
        counts = (
            '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;margin-bottom:16px;">'
            '<tr>'
            '<td style="padding:8px 16px;background:#f6f7f9;border:1px solid #dee2e6;text-align:center;">'
            '<div style="font-size:22px;font-weight:700;">%(total)d</div>'
            '<div style="color:#666;font-size:11px;text-transform:uppercase;">Rows</div>'
            '</td>'
            '<td style="padding:8px 16px;background:#d1e7dd;border:1px solid #badbcc;text-align:center;">'
            '<div style="font-size:22px;font-weight:700;color:#0f5132;">%(ok)d</div>'
            '<div style="color:#0f5132;font-size:11px;text-transform:uppercase;">Success</div>'
            '</td>'
            '<td style="padding:8px 16px;background:#f8d7da;border:1px solid #f5c2c7;text-align:center;">'
            '<div style="font-size:22px;font-weight:700;color:#842029;">%(err)d</div>'
            '<div style="color:#842029;font-size:11px;text-transform:uppercase;">Errors</div>'
            '</td>'
            '<td style="padding:8px 16px;background:#e9ecef;border:1px solid #dee2e6;text-align:center;">'
            '<div style="font-size:22px;font-weight:700;color:#6c757d;">%(skip)d</div>'
            '<div style="color:#6c757d;font-size:11px;text-transform:uppercase;">Skipped</div>'
            '</td>'
            '</tr>'
            '</table>'
        ) % {
            'total': self.total_rows or 0,
            'ok': self.success_count or 0,
            'err': self.error_count or 0,
            'skip': self.skip_count or 0,
        }
        # Row-level table (capped)
        cap = 500
        lines = self.line_ids.sorted(lambda l: l.row_number or 0)[:cap]
        row_html_parts = []
        for l in lines:
            status = (l.status or '').lower()
            bg = ('#d1e7dd' if status in ('created', 'updated', 'deleted')
                  else '#f8d7da' if status == 'error'
                  else '#f6f7f9')
            color = ('#0f5132' if status in ('created', 'updated', 'deleted')
                     else '#842029' if status == 'error'
                     else '#6c757d')
            row_html_parts.append(
                '<tr>'
                '<td style="padding:4px 8px;border-bottom:1px solid #eee;font-family:monospace;">%d</td>'
                '<td style="padding:4px 8px;border-bottom:1px solid #eee;background:%s;color:%s;font-weight:600;">%s</td>'
                '<td style="padding:4px 8px;border-bottom:1px solid #eee;">%s</td>'
                '<td style="padding:4px 8px;border-bottom:1px solid #eee;">%s</td>'
                '</tr>' % (
                    l.row_number or 0,
                    bg, color, (l.status or '').upper(),
                    l.res_id or '',
                    (l.message or '').replace('<', '&lt;').replace('>', '&gt;'),
                )
            )
        row_table = ''
        if row_html_parts:
            row_table = (
                '<h3 style="font-family:Arial,sans-serif;font-size:15px;margin:20px 0 8px;">'
                'Row results (%d shown)</h3>'
                '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:12px;width:100%%;">'
                '<thead><tr style="background:#f6f7f9;">'
                '<th style="padding:6px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Row</th>'
                '<th style="padding:6px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Status</th>'
                '<th style="padding:6px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Record ID</th>'
                '<th style="padding:6px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Message</th>'
                '</tr></thead><tbody>%s</tbody></table>'
            ) % (len(lines), ''.join(row_html_parts))
        overflow_notice = ''
        if len(self.line_ids) > cap:
            overflow_notice = (
                '<p style="font-family:Arial,sans-serif;font-size:12px;color:#6c757d;">'
                'Only the first %d rows are shown here. Full details are in '
                'the attached error report CSV.</p>'
            ) % cap
        return (
            '<div style="font-family:Arial,sans-serif;color:#1f2937;">'
            '<h2 style="font-size:18px;margin:0 0 8px;">Data Loader Job Report</h2>'
            '<p style="color:#6c757d;font-size:13px;margin:0 0 16px;">'
            'Your %s job finished. See the summary and per-row breakdown below. '
            'Attached: the original source file%s%s.'
            '</p>%s%s%s%s</div>'
        ) % (
            dict(self._fields['mode'].selection).get(self.mode, self.mode or ''),
            (', an error report CSV' if self.error_report else ''),
            (', the exported CSV' if self.exported_file else ''),
            deal_summary, counts, row_table, overflow_notice,
        )

    # ================================================================
    # Error report CSV
    # ================================================================
    def _render_error_report(self):
        self.ensure_one()
        errors = self.line_ids.filtered(lambda l: l.status == 'error')
        if not errors:
            return
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['row', 'status', 'message', 'payload_json'])
        for l in errors:
            writer.writerow([l.row_number, l.status, l.message or '', l.payload or ''])
        payload = buf.getvalue().encode('utf-8')
        fname = 'errors_%s.csv' % (self.name or 'job').replace('/', '_')
        self.write({
            'error_report': base64.b64encode(payload),
            'error_report_filename': fname,
        })

    # ================================================================
    # Small niceties
    # ================================================================
    def action_reset_to_draft(self):
        for job in self:
            job.write({
                'state': 'draft',
                'total_rows': 0, 'success_count': 0,
                'error_count': 0, 'skip_count': 0,
                'started_at': False, 'finished_at': False,
                'error_report': False, 'error_report_filename': False,
                'exported_file': False, 'exported_filename': False,
            })
            job.line_ids.unlink()
        return True

    def action_view_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Job Lines: %s') % self.name,
            'res_model': 'mv.dataloader.line',
            'view_mode': 'list,form',
            'domain': [('job_id', '=', self.id)],
            'context': {'default_job_id': self.id},
        }


    # ================================================================
    # Wizard RPC surface (Phase 17b)
    # ================================================================
    def dl_snapshot(self):
        """Return a single-payload snapshot of everything the OWL
        wizard needs to render every step of this job. Cuts a bunch
        of round-trips down to one."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name or '',
            'mode': self.mode,
            'state': self.state,
            'model_id': self.model_id.id or False,
            'model_name': self.model_name or '',
            'model_label': self.model_id.name or '',
            'source_filename': self.source_filename or '',
            'has_file': bool(self.source_file),
            'header_row': self.header_row,
            'delimiter': self.delimiter,
            'match_field_id': self.match_field_id.id or False,
            'match_field_name': self.match_field_id.name or '',
            'match_by': self.match_by,
            'on_error': self.on_error,
            'export_domain': self.export_domain or '[]',
            'export_field_ids': [
                {'id': f.id, 'name': f.name, 'label': f.field_description or f.name}
                for f in self.export_field_ids
            ],
            'exported_filename': self.exported_filename or '',
            'has_export': bool(self.exported_file),
            'total_rows': self.total_rows,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'skip_count': self.skip_count,
            'started_at': self.started_at.isoformat() if self.started_at else False,
            'finished_at': self.finished_at.isoformat() if self.finished_at else False,
            'duration_seconds': self.duration_seconds,
            'has_error_report': bool(self.error_report),
            'error_report_filename': self.error_report_filename or '',
            'mapping': [
                {
                    'id': m.id,
                    'sequence': m.sequence,
                    'source_column': m.source_column or '',
                    'target_field_id': m.target_field_id.id or False,
                    'target_field_name': m.target_field_id.name or '',
                    'target_ttype': m.target_field_id.ttype or '',
                    'target_relation': m.target_field_id.relation or '',
                    'match_key_for_m2o': m.match_key_for_m2o or 'name',
                    'skip': m.skip,
                }
                for m in self.mapping_ids
            ],
            'lines': [
                {
                    'id': l.id,
                    'row_number': l.row_number,
                    'status': l.status,
                    'res_id': l.res_id,
                    'message': l.message or '',
                }
                for l in self.line_ids[:200]  # cap for UI
            ],
        }

    @api.model
    def dl_list_models(self):
        """List of ir.model records the wizard offers in the model
        picker. Excludes transient / abstract models."""
        Model = self.env['ir.model'].search([
            ('transient', '=', False),
            ('abstract', '=', False),
        ], order='name asc')
        return [
            {'id': m.id, 'name': m.name or '', 'model': m.model or ''}
            for m in Model
        ]

    @api.model
    def dl_list_fields(self, model_id):
        """Stored fields on the given model, for the mapping /
        match-field / export-fields pickers."""
        if not model_id:
            return []
        fields_r = self.env['ir.model.fields'].search([
            ('model_id', '=', int(model_id)),
            ('store', '=', True),
        ], order='name asc')
        return [
            {
                'id': f.id,
                'name': f.name,
                'label': f.field_description or f.name,
                'ttype': f.ttype,
                'relation': f.relation or '',
                'required': f.required,
            }
            for f in fields_r
        ]

    def dl_save_mapping(self, mapping_patches):
        """Bulk update mapping_ids from the wizard. Each patch:
            {id, target_field_id, match_key_for_m2o, skip}
        """
        self.ensure_one()
        by_id = {m.id: m for m in self.mapping_ids}
        for p in mapping_patches or []:
            rec = by_id.get(int(p.get('id') or 0))
            if not rec:
                continue
            rec.write({
                'target_field_id': p.get('target_field_id') or False,
                'match_key_for_m2o': (p.get('match_key_for_m2o') or 'name').strip(),
                'skip': bool(p.get('skip')),
            })
        return True


# =====================================================================
# mv.dataloader.mapping - one row per source column
# =====================================================================
class MvDataloaderMapping(models.Model):
    _name = 'mv.dataloader.mapping'
    _description = 'Data Loader Column Mapping'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'mv.dataloader.job', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    source_column = fields.Char(string='CSV Column', required=True)
    target_field_id = fields.Many2one(
        'ir.model.fields', string='Target Field',
        domain="[('model_id', '=', parent.model_id), ('store', '=', True)]",
    )
    target_field_name = fields.Char(
        related='target_field_id.name', store=True, readonly=True,
    )
    # NOTE: target_ttype used to be a related Char pointing at
    # ir.model.fields.ttype (which is a Selection). That produced
    # "Type of related field ... is inconsistent" at boot. The
    # wizard reads the ttype directly off target_field_id inside
    # dl_snapshot(), so this stored field isn't needed anywhere.
    # For m2o / m2m: what lookup key to use in the source cell
    match_key_for_m2o = fields.Char(
        default='name', string='M2O Lookup By',
        help='Field name on the related model used to resolve the CSV value. '
             'Also accepts "id" or "external_id".',
    )
    skip = fields.Boolean(default=False, string='Skip')


# =====================================================================
# mv.dataloader.line - one row per processed source row (audit trail)
# =====================================================================
class MvDataloaderLine(models.Model):
    _name = 'mv.dataloader.line'
    _description = 'Data Loader Row Result'
    _order = 'job_id desc, row_number asc, id'

    job_id = fields.Many2one(
        'mv.dataloader.job', required=True, ondelete='cascade', index=True,
    )
    row_number = fields.Integer(string='Row #')
    status = fields.Selection([
        ('preview',  'Preview OK'),
        ('created',  'Created'),
        ('updated',  'Updated'),
        ('deleted',  'Deleted'),
        ('skipped',  'Skipped'),
        ('error',    'Error'),
    ], default='preview')
    res_id = fields.Integer(string='Record ID')
    message = fields.Char(string='Message')
    payload = fields.Text(string='Row Payload (JSON)')


# =====================================================================
# Helpers
# =====================================================================
class _ValidationError(Exception):
    """Raised by row-level validation - caught, logged to a line."""


def _guess_field(col, by_name, by_label):
    """Auto-map a CSV header cell to an ir.model.fields."""
    if not col:
        return None
    c = col.strip()
    # Exact name
    if c in by_name:
        return by_name[c]
    # snake_case + lowercased
    snake = _to_snake(c)
    if snake in by_name:
        return by_name[snake]
    # Human label match
    return by_label.get(c.lower())


def _to_snake(s):
    """'Customer Name' -> 'customer_name'."""
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch.lower())
        elif out and out[-1] != '_':
            out.append('_')
    return ''.join(out).strip('_')


def _flatten_cell(v):
    """Turn a read() value into something safe to write into CSV."""
    if v is False or v is None:
        return ''
    if isinstance(v, tuple):
        # Many2one -> (id, display_name)
        return v[1] if len(v) > 1 else v[0]
    if isinstance(v, list):
        return ','.join(str(x) for x in v)
    if isinstance(v, (datetime,)):
        return v.isoformat()
    return v
