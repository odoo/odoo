# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time, UTC

from odoo import api, fields, models
from odoo.exceptions import ValidationError


def _fmt_range(record, date_from, date_to):
    if not date_from:
        return ''
    df = fields.Datetime.context_timestamp(record, date_from)

    def _t(dt):
        h = dt.strftime('%I:%M %p').lstrip('0')
        return f"{dt.strftime('%b')} {dt.day}, {h}"
    if not date_to:
        return _t(df)
    dt = fields.Datetime.context_timestamp(record, date_to)
    if df.date() == dt.date():
        return f"{_t(df)} -> {dt.strftime('%I:%M %p').lstrip('0')}"
    return f"{_t(df)} -> {_t(dt)}"


class HrTimeRuleRegenerateWizard(models.TransientModel):
    _name = 'hr.time.rule.regenerate.wizard'
    _description = 'Reprocess Time Rules'

    rule_ids = fields.Many2many('hr.time.rule', required=True, readonly=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees',
                                    help='Leave empty to include all employees.')
    source_model_filter = fields.Selection([
        ('all', 'All'),
    ], default='all',
        help='Restricts Find to the selected record type.')
    scope = fields.Selection([
        ('all', 'All records'),
        ('range', 'From'),
    ], default='all', required=True)
    date_from = fields.Date()
    date_to = fields.Date()
    step = fields.Selection([
        ('find', 'Find'),
        ('restore', 'Restore'),
        ('rerun', 'Rerun'),
        ('done', 'Done'),
    ], default='find', required=True)
    line_ids = fields.One2many('hr.time.rule.regenerate.wizard.line', 'wizard_id')
    restored_line_ids = fields.One2many(
        'hr.time.rule.regenerate.wizard.line', 'wizard_id',
        domain=[('is_restored', '=', True)],
    )
    new_output_line_ids = fields.One2many(
        'hr.time.rule.regenerate.wizard.line', 'wizard_id',
        domain=[('is_new_output', '=', True)],
    )
    removed_line_ids = fields.One2many('hr.time.rule.regenerate.wizard.removed', 'wizard_id')
    error_line_ids = fields.One2many('hr.time.rule.regenerate.wizard.error', 'wizard_id')
    has_errors = fields.Boolean(compute='_compute_has_errors')
    has_removed = fields.Boolean(compute='_compute_has_removed')
    has_restored = fields.Boolean(compute='_compute_has_restored')

    @api.depends('error_line_ids')
    def _compute_has_errors(self):
        for wiz in self:
            wiz.has_errors = bool(wiz.error_line_ids)

    has_outputs = fields.Boolean(compute='_compute_has_outputs')

    @api.depends('line_ids.is_output', 'line_ids.selected')
    def _compute_has_outputs(self):
        for wiz in self:
            wiz.has_outputs = any(l.is_output and l.selected for l in wiz.line_ids)

    @api.depends('removed_line_ids')
    def _compute_has_removed(self):
        for wiz in self:
            wiz.has_removed = bool(wiz.removed_line_ids)

    @api.depends('restored_line_ids')
    def _compute_has_restored(self):
        for wiz in self:
            wiz.has_restored = bool(wiz.restored_line_ids)

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self._description,
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _date_domain(self, span_start_field):
        if self.scope != 'range':
            return []
        domain = []
        if self.date_from:
            start_utc = datetime.combine(self.date_from, time.min).replace(tzinfo=UTC)
            domain.append((span_start_field, '>=', start_utc.replace(tzinfo=None)))
        if self.date_to:
            end_utc = datetime.combine(self.date_to, time.max).replace(tzinfo=UTC)
            domain.append((span_start_field, '<=', end_utc.replace(tzinfo=None)))
        return domain

    def _employee_domain(self):
        if not self.employee_ids:
            return []
        return [('employee_id', 'in', self.employee_ids.ids)]

    def _get_source_models(self):
        """Return Model env objects for all concrete mixin implementors installed."""
        mixin_cls = self.env.registry['hr.time.rule.source.mixin']
        return [
            self.env[name]
            for name, cls in self.env.registry.models.items()
            if not cls._abstract and mixin_cls in cls.__mro__
        ]

    def _collect_sources(self):
        """Return list of (source_model, active_record, is_output, original_id, rule).

        is_output=True  -> active output produced by this rule
        is_output=False -> virgin candidate matching condition WETs, no output yet
        """
        result = []
        rule_map = {r.id: r for r in self.rule_ids}
        seen = {}   # model_name -> set of record ids

        for Model in self._get_source_models():
            model_name = Model._name
            source_field = Model._time_rule_source_field
            span_start = Model._time_rule_span_start_field
            extra = Model._time_rule_wizard_extra_domain()
            seen[model_name] = set()

            if self.source_model_filter not in ('all', model_name):
                continue

            # outputs (time_rule_id in rules) and their remainder slices (time_rule_id=False).
            # collect in two passes so we only keep remainders whose original also has an output
            # from this wizard's rules (avoids cross-rule contamination on other models).
            originals_with_output = set()
            pending_remainders = []
            for out in Model.sudo().search([
                (source_field, '!=', False),
                '|', ('time_rule_id', '=', False), ('time_rule_id', 'in', self.rule_ids.ids),
            ] + extra + self._date_domain(span_start) + self._employee_domain()):
                if out.id in seen[model_name]:
                    continue
                seen[model_name].add(out.id)
                original_id = out.with_context(active_test=False)[source_field].id or 0
                if out.time_rule_id:
                    originals_with_output.add(original_id)
                    result.append((model_name, out, True, original_id, rule_map.get(out.time_rule_id.id)))
                else:
                    pending_remainders.append((out, original_id))
            for out, original_id in pending_remainders:
                if original_id in originals_with_output:
                    result.append((model_name, out, True, original_id, None))

            # pure-allocation rules — delegate to a method overridden by hr_holidays
            result.extend(self._collect_pure_alloc_rule_sources(Model, source_field, span_start, extra, seen[model_name]))

            # virgin candidates — only in range scope
            if self.scope != 'range':
                continue
            for rule in self.rule_ids:
                wet_ids = rule.condition_work_entry_type_ids.ids
                if not wet_ids:
                    continue
                for rec in Model.sudo().search([
                    ('work_entry_type_id', 'in', wet_ids),
                    (source_field, '=', False),
                    ('time_rule_id', '=', False),
                ] + extra + self._date_domain(span_start) + self._employee_domain()):
                    if rec.id not in seen[model_name]:
                        seen[model_name].add(rec.id)
                        result.append((model_name, rec, False, 0, rule))

        return result

    def _collect_pure_alloc_rule_sources(self, Model, source_field, span_start, extra, seen_ids):
        return []

    @api.model
    def action_open_from_records(self, records):
        """Open the wizard pre-filled from a selection of source records."""
        rules = self.env['hr.time.rule'].search([])
        employees = records.mapped('employee_id')
        model_name = records._name
        start_field = records._time_rule_span_start_field
        end_field = records._time_rule_span_end_field
        dates_start = records.filtered(start_field).mapped(start_field)
        dates_end = records.filtered(end_field).mapped(end_field)
        valid_filters = {k for k, _label in self.fields_get(['source_model_filter'])['source_model_filter']['selection']}
        vals = {
            'rule_ids': [(6, 0, rules.ids)],
            'employee_ids': [(6, 0, employees.ids)],
            'source_model_filter': model_name if model_name in valid_filters else 'all',
            'scope': 'range' if records else 'all',
        }
        if dates_start:
            vals['date_from'] = min(dates_start).date()
        if dates_end:
            vals['date_to'] = max(dates_end).date()
        wizard = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': self._description,
            'res_model': self._name,
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
        }

    def action_find(self):
        self.ensure_one()
        sources = self._collect_sources()
        self.line_ids.unlink()
        self.removed_line_ids.unlink()
        self.error_line_ids.unlink()
        line_vals = []
        for model_name, rec, is_output, original_id, rule in sources:
            line_vals.append(self._source_to_line_vals(model_name, rec, is_output, original_id, rule))
        if line_vals:
            self.env['hr.time.rule.regenerate.wizard.line'].create(line_vals)
        self.step = 'restore'
        return self._reopen()

    def _source_to_line_vals(self, model_name, rec, is_output=True, original_id=0, rule=None):
        Model = self.env[model_name]
        date_from = rec[Model._time_rule_span_start_field]
        date_to = rec[Model._time_rule_span_end_field]
        return {
            'wizard_id': self.id,
            'rule_id': rule.id if rule else False,
            'source_model': model_name,
            'source_id': rec.id,
            'is_output': is_output,
            'source_original_id': original_id,
            'employee_id': rec.employee_id.id,
            'date': date_from.date() if date_from else False,
            'date_from': date_from,
            'date_to': date_to,
            'work_entry_type_id': rec.work_entry_type_id.id,
        }

    def _line_to_error_vals(self, line, error_msg):
        return {
            'wizard_id': self.id,
            'employee_id': line.employee_id.id,
            'date': line.date,
            'date_from': line.date_from,
            'date_to': line.date_to,
            'work_entry_type_id': line.work_entry_type_id.id,
            'error': error_msg,
        }

    def _group_originals(self, output_lines):
        """Groups output lines by their original source.
        Returns an ordered list of (model, original_record, representative_line) tuples.
        """
        seen = {}
        for line in output_lines:
            if not line.source_original_id:
                continue
            key = (line.source_model, line.source_original_id)
            seen.setdefault(key, line)
        groups = []
        for (model, orig_id), rep_line in seen.items():
            original = self.env[model].with_context(active_test=False).sudo().browse(orig_id)
            groups.append((model, original, rep_line))
        return groups, []

    def action_restore(self):
        self.ensure_one()
        self.error_line_ids.unlink()
        self.removed_line_ids.unlink()

        output_lines = self.line_ids.filtered(lambda l: l.selected and l.is_output)
        groups, _empties = self._group_originals(output_lines)

        removed_by_key = {}
        for line in output_lines:
            if not line.source_original_id:
                continue
            removed_by_key.setdefault((line.source_model, line.source_original_id), []).append({
                'wizard_id': self.id,
                'employee_id': line.employee_id.id,
                'date': line.date,
                'date_from': line.date_from,
                'date_to': line.date_to,
                'work_entry_type_id': line.work_entry_type_id.id,
            })

        error_vals = []
        survivor_line_vals = []
        removed_vals = []

        for model, original, rep_line in groups:
            try:
                with self.env.cr.savepoint():
                    original._undo_time_rules()
            except ValidationError as e:
                error_vals.append(
                    self._line_to_error_vals(rep_line, e.args[0] if e.args else str(e))
                )
            else:
                removed_vals.extend(removed_by_key.get((rep_line.source_model, rep_line.source_original_id), []))
                vals = self._source_to_line_vals(model, original, False, 0)
                vals['is_restored'] = True
                survivor_line_vals.append(vals)

        if error_vals:
            self.env['hr.time.rule.regenerate.wizard.error'].create(error_vals)
        if removed_vals:
            self.env['hr.time.rule.regenerate.wizard.removed'].create(removed_vals)

        self.line_ids.filtered('is_output').unlink()
        if survivor_line_vals:
            self.env['hr.time.rule.regenerate.wizard.line'].create(survivor_line_vals)

        self.step = 'rerun'
        return self._reopen()

    def _apply_rerun(self):
        selected = self.line_ids.filtered('selected')
        error_vals = []
        for line in selected:
            src = self.env[line.source_model].with_context(active_test=False).sudo().browse(line.source_id)
            try:
                with self.env.cr.savepoint():
                    src._trigger_time_rules(include_deficit=True)
            except ValidationError as e:
                error_vals.append(self._line_to_error_vals(line, e.args[0] if e.args else str(e)))
        return error_vals

    def _collect_new_outputs(self, processed_source_ids):
        """Find outputs/remainders created for the given source IDs across all source models."""
        new_output_vals = []
        for Model in self._get_source_models():
            source_field = Model._time_rule_source_field
            extra = Model._time_rule_wizard_extra_domain()
            for out in Model.sudo().search(
                [(source_field, 'in', list(processed_source_ids))] + extra
            ):
                vals = self._source_to_line_vals(Model._name, out, bool(out.time_rule_id), out[source_field].id or 0)
                vals['is_new_output'] = True
                new_output_vals.append(vals)
        return new_output_vals

    def action_run(self):
        """Run rules on all found source records without undoing existing outputs."""
        self.ensure_one()
        self.error_line_ids.unlink()

        all_lines = self.line_ids.filtered(lambda l: l.selected and not l.is_output)
        error_vals = []
        processed_source_ids = set()
        survivor_line_vals = []

        for line in all_lines:
            src = self.env[line.source_model].sudo().browse(line.source_id)
            try:
                with self.env.cr.savepoint():
                    src._trigger_time_rules(include_deficit=True)
            except ValidationError as e:
                error_vals.append(self._line_to_error_vals(line, e.args[0] if e.args else str(e)))
            else:
                processed_source_ids.add(line.source_id)
                vals = self._source_to_line_vals(line.source_model, src, False, 0)
                vals['is_restored'] = True
                survivor_line_vals.append(vals)

        if error_vals:
            self.env['hr.time.rule.regenerate.wizard.error'].create(error_vals)
            self.step = 'rerun'
            return self._reopen()

        if survivor_line_vals:
            self.env['hr.time.rule.regenerate.wizard.line'].create(survivor_line_vals)

        new_output_vals = self._collect_new_outputs(processed_source_ids)
        if new_output_vals:
            self.env['hr.time.rule.regenerate.wizard.line'].create(new_output_vals)

        self.step = 'done'
        return self._reopen()

    def action_rerun(self):
        self.ensure_one()
        self.error_line_ids.unlink()

        processed_source_ids = {l.source_id for l in self.line_ids.filtered('selected')}

        error_vals = self._apply_rerun()
        if error_vals:
            self.env['hr.time.rule.regenerate.wizard.error'].create(error_vals)
            self.step = 'rerun'
            return self._reopen()

        new_output_vals = self._collect_new_outputs(processed_source_ids)
        if new_output_vals:
            self.env['hr.time.rule.regenerate.wizard.line'].create(new_output_vals)

        self.step = 'done'
        return self._reopen()


class HrTimeRuleRegenerateWizardLine(models.TransientModel):
    _name = 'hr.time.rule.regenerate.wizard.line'
    _description = 'Regenerate Wizard Line'
    _order = 'employee_id, date_from'

    def action_open_source(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.source_model,
            'res_id': self.source_id,
            'view_mode': 'form',
            'target': 'new',
        }

    wizard_id = fields.Many2one('hr.time.rule.regenerate.wizard', required=True, ondelete='cascade')
    rule_id = fields.Many2one('hr.time.rule', readonly=True)
    selected = fields.Boolean(default=True)
    is_output = fields.Boolean(default=True, readonly=True)
    is_restored = fields.Boolean(default=False, readonly=True)
    is_new_output = fields.Boolean(default=False, readonly=True)
    kind = fields.Char(compute='_compute_kind')
    date_range = fields.Char(compute='_compute_date_range')

    @api.depends('is_output')
    def _compute_kind(self):
        for line in self:
            line.kind = 'Output' if line.is_output else 'Source'

    @api.depends('date_from', 'date_to')
    def _compute_date_range(self):
        for line in self:
            line.date_range = _fmt_range(line, line.date_from, line.date_to)

    source_model = fields.Char(required=True)
    source_id = fields.Integer(required=True)
    source_original_id = fields.Integer()
    employee_id = fields.Many2one('hr.employee', readonly=True)
    date = fields.Date(readonly=True)
    date_from = fields.Datetime(string='Start', readonly=True)
    date_to = fields.Datetime(string='End', readonly=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Time Type', readonly=True)
    color = fields.Integer(related='work_entry_type_id.color')


class HrTimeRuleRegenerateWizardRemoved(models.TransientModel):
    _name = 'hr.time.rule.regenerate.wizard.removed'
    _description = 'Regenerate Wizard Removed Output'
    _order = 'employee_id, date_from'

    wizard_id = fields.Many2one('hr.time.rule.regenerate.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', readonly=True)
    date = fields.Date(readonly=True)
    date_from = fields.Datetime(string='Start', readonly=True)
    date_to = fields.Datetime(string='End', readonly=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Time Type', readonly=True)
    color = fields.Integer(related='work_entry_type_id.color')
    date_range = fields.Char(compute='_compute_date_range')

    @api.depends('date_from', 'date_to')
    def _compute_date_range(self):
        for line in self:
            line.date_range = _fmt_range(line, line.date_from, line.date_to)


class HrTimeRuleRegenerateWizardError(models.TransientModel):
    _name = 'hr.time.rule.regenerate.wizard.error'
    _description = 'Regenerate Wizard Error'
    _order = 'employee_id, date_from'

    wizard_id = fields.Many2one('hr.time.rule.regenerate.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', readonly=True)
    date = fields.Date(readonly=True)
    date_from = fields.Datetime(string='Start', readonly=True)
    date_to = fields.Datetime(string='End', readonly=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Time Type', readonly=True)
    color = fields.Integer(related='work_entry_type_id.color')
    error = fields.Text(readonly=True)
    short_error = fields.Char(compute='_compute_short_error', readonly=True)

    @api.depends('error')
    def _compute_short_error(self):
        for rec in self:
            msg = rec.error or ''
            rec.short_error = msg[:80] + '…' if len(msg) > 80 else msg
