# -*- coding: utf-8 -*-
"""Phase 14 v3 - Salesforce-style Report Builder (foundation).

Models:
  - mv.report           : the saved report (name, owner, primary model)
  - mv.report.column    : ordered display columns (drag-to-reorder in UI)
  - mv.report.filter    : filter rows with operator + value
  - mv.report.group     : group-by ladder (stub - UI iterates)
  - mv.report.sort      : sort ladder (stub - UI iterates)

The OWL client action (see static/src/js/report_builder/) drives the UI
and talks to RPC methods on mv.report (see phase14_reports_rpc.py).
"""
import ast
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# ---------------------------------------------------------------------
# mv.report - top-level saved report
# ---------------------------------------------------------------------
class MvReport(models.Model):
    _name = 'mv.report'
    _description = 'MV Saved Report'
    _order = 'sequence, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Report Name', required=True, tracking=True,
                       default=lambda self: _('New Report'))
    description = fields.Text(string='Description')
    sequence = fields.Integer(default=10)

    # Phase 14 v4: reports are anchored on a Report Type, which
    # defines the base model + joined models. model_id is now a
    # derived convenience for legacy code that still needs "which is
    # the primary model" (== report_type_id.base_model_id).
    report_type_id = fields.Many2one(
        'mv.report.type', string='Report Type',
        ondelete='cascade',
        help='The Report Type provides the base model + joined models. '
             'Fields for the Report Builder are drawn from all of them.',
    )
    model_id = fields.Many2one(
        'ir.model', string='Primary Model',
        related='report_type_id.base_model_id', store=True, readonly=True,
    )
    model_name = fields.Char(related='model_id.model', store=True, readonly=True)

    column_ids = fields.One2many('mv.report.column', 'report_id',
                                 string='Columns', copy=True)
    filter_ids = fields.One2many('mv.report.filter', 'report_id',
                                 string='Filters', copy=True)
    group_ids = fields.One2many('mv.report.group', 'report_id',
                                string='Groups', copy=True)
    sort_ids = fields.One2many('mv.report.sort', 'report_id',
                               string='Sorts', copy=True)

    # Sharing -----------------------------------------------------------
    owner_id = fields.Many2one('res.users', string='Owner', required=True,
                               default=lambda self: self.env.user,
                               tracking=True)
    is_public = fields.Boolean(string='Visible to All Users')
    shared_user_ids = fields.Many2many(
        'res.users', relation='mv_report_shared_user_rel',
        column1='report_id', column2='user_id',
        string='Shared With',
    )

    last_run_date = fields.Datetime(string='Last Run', readonly=True)

    # Cached dynamic list view rebuilt every time the report is Run -
    # contains only the columns the planner selected. Stored on the
    # report so we update its arch in place rather than leaking a new
    # ir.ui.view row per Run.
    dynamic_view_id = fields.Many2one(
        'ir.ui.view', string='Dynamic List View',
        ondelete='set null', readonly=True, copy=False,
    )

    # --- Actions -----------------------------------------------------
    def action_open_builder(self):
        """Launch the OWL report builder for this report.

        Odoo 19's ControllerComponent.onMounted -> pushState ->
        makeState path is the one that crashes on weird actions.
        For a client action, the minimal viable shape is just
        type + tag + (optional) name + params; let the framework
        compute its own URL state defaults rather than feeding it
        a `views` array that doesn't match its expected schema.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'mv_report_builder',
            'name': self.name or _('Report Builder'),
            'params': {'report_id': self.id},
        }

    def action_run(self):
        """Run the report - open the primary model's list view, but
        with a *dynamic* ir.ui.view that contains only the columns the
        planner selected, in the order they were dragged, with the
        report's sort applied as default_order and the report's groups
        applied via the action's context group_by.

        Why dynamic-view rather than the default list view: the user
        explicitly picked N columns; opening the model's default list
        view shows every default column (often dozens), defeating the
        report.

        Odoo 19's _preprocessAction calls .map() on action.views, so
        we always pass an explicit views array.
        """
        self.ensure_one()
        self.write({'last_run_date': fields.Datetime.now()})

        view_id = self._sync_dynamic_view()

        # Group-by via context (used by the list view's group banner).
        groups = self.group_ids.sorted('sequence')
        context = {}
        gb = [g.field_id.name for g in groups if g.field_id]
        if gb:
            context['group_by'] = gb

        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': self.model_id.model,
            'view_mode': 'list,form',
            'views': [(view_id, 'list'), (False, 'form')],
            'domain': self._build_domain(),
            'context': context,
            'target': 'current',
        }

    def _sync_dynamic_view(self):
        """Build or refresh the ir.ui.view for this report's Run, and
        return its id. Idempotent - one ir.ui.view row per mv.report."""
        self.ensure_one()
        from odoo.tools import html_escape as _esc
        cols = self.column_ids.sorted('sequence')
        field_lines = []
        for c in cols:
            if not c.field_id:
                continue
            fname = c.field_id.name
            label = c.field_label or ''
            if label:
                field_lines.append(
                    '<field name="%s" string="%s"/>' % (fname, _esc(label))
                )
            else:
                field_lines.append('<field name="%s"/>' % fname)

        # default_order from sort ladder
        order_parts = []
        for s in self.sort_ids.sorted('sequence'):
            if s.field_id:
                direction = 'desc' if s.direction == 'desc' else 'asc'
                order_parts.append('%s %s' % (s.field_id.name, direction))
        order_attr = (
            ' default_order="%s"' % _esc(', '.join(order_parts))
            if order_parts else ''
        )

        title = _esc(self.name or 'Report')
        if field_lines:
            arch = '<list string="%s"%s>%s</list>' % (
                title, order_attr, ''.join(field_lines)
            )
        else:
            # No columns picked yet - empty list (Odoo requires at
            # least the root element).
            arch = '<list string="%s"/>' % title

        Vw = self.env['ir.ui.view'].sudo()
        vals = {
            'name': 'mv.report.dynamic.%s' % self.id,
            'model': self.model_id.model,
            'type': 'list',
            'arch_base': arch,
            'priority': 99,
        }
        if self.dynamic_view_id:
            # If the user switched primary model between Runs, the
            # cached view's model is stale - rewrite it.
            self.dynamic_view_id.write(vals)
            return self.dynamic_view_id.id
        view = Vw.create(vals)
        # bypass write tracking on the report - we're just caching a
        # backref. Use sudo to dodge owner-only write rule.
        self.sudo().write({'dynamic_view_id': view.id})
        return view.id

    # --- Domain builder ---------------------------------------------
    def _build_domain(self):
        """Turn mv.report.filter rows into an Odoo domain. AND-only for
        now; OR groups are a follow-up."""
        self.ensure_one()
        domain = []
        for f in self.filter_ids.sorted('sequence'):
            term = f._to_domain_term()
            if term:
                domain.append(term)
        return domain


# ---------------------------------------------------------------------
# mv.report.column - one display column on a report
# ---------------------------------------------------------------------
class MvReportColumn(models.Model):
    _name = 'mv.report.column'
    _description = 'Report Column'
    _order = 'sequence, id'

    report_id = fields.Many2one('mv.report', required=True, ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', required=True,
                               ondelete='cascade')
    field_name = fields.Char(related='field_id.name', store=True, readonly=True)
    field_label = fields.Char(string='Label',
                              help='Override label shown in the report. '
                                   'Leave empty to use the field\'s default.')
    sequence = fields.Integer(default=10)
    # Phase 14 v4: dotted path from the report's base model to this
    # field. Empty/blank means the field lives on the base model.
    # E.g. 'advertiser_id.name' means "advertiser (m2o from base) . name".
    path = fields.Char(
        string='Path',
        help='Dotted access path from the base model to this field '
             '(e.g. advertiser_id.name). Empty = base-model field.',
    )
    node_id = fields.Many2one(
        'mv.report.type.node', string='From Node', ondelete='set null',
        help='The Report Type node this field was drawn from. '
             'Blank = base model.',
    )

    # Aggregation - stub for now. UI will surface a Selection dropdown
    # next iteration; backend just stores the choice.
    aggregation = fields.Selection([
        ('none', 'None'),
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('count', 'Count'),
        ('count_distinct', 'Distinct Count'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
    ], string='Aggregation', default='none')


# ---------------------------------------------------------------------
# mv.report.filter - one filter row
# ---------------------------------------------------------------------
class MvReportFilter(models.Model):
    _name = 'mv.report.filter'
    _description = 'Report Filter'
    _order = 'sequence, id'

    report_id = fields.Many2one('mv.report', required=True, ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', required=True,
                               ondelete='cascade')
    field_name = fields.Char(related='field_id.name', store=True, readonly=True)
    # Phase 14 v4: dotted path from the report's base model.
    path = fields.Char(string='Path')
    node_id = fields.Many2one(
        'mv.report.type.node', string='From Node',
        ondelete='set null',
    )
    operator = fields.Selection([
        ('=', 'Equals'),
        ('!=', 'Not Equals'),
        ('ilike', 'Contains'),
        ('not ilike', 'Does Not Contain'),
        ('=like', 'Starts With'),
        ('like%', 'Ends With'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('>=', 'Greater or Equal'),
        ('<=', 'Less or Equal'),
        ('in', 'In'),
        ('not in', 'Not In'),
    ], string='Operator', default='=', required=True)
    value = fields.Char(string='Value',
                        help='Raw value (string, number, true/false, or '
                             'comma-separated list for in/not in).')
    sequence = fields.Integer(default=10)
    # Logical op connecting this row to the previous one. AND only for
    # the v3 foundation; OR groups follow.
    logical_op = fields.Selection([('and', 'AND'), ('or', 'OR')],
                                  string='Logical Op', default='and')

    def _to_domain_term(self):
        """Convert this filter row into a domain tuple."""
        self.ensure_one()
        if not self.field_id:
            return None
        op = self.operator or '='
        raw = self.value or ''
        # Coerce value by field type
        ttype = self.field_id.ttype
        try:
            if ttype in ('integer', 'monetary'):
                val = int(raw) if raw else 0
            elif ttype == 'float':
                val = float(raw) if raw else 0.0
            elif ttype == 'boolean':
                val = raw.lower() in ('1', 'true', 't', 'yes')
            elif op in ('in', 'not in'):
                val = [v.strip() for v in raw.split(',') if v.strip()]
            elif op in ('ilike', 'not ilike'):
                val = raw
            elif op == '=like':
                # Starts-with: append % wildcard
                val = (raw or '') + '%'
                op = 'ilike'
            elif op == 'like%':
                # Ends-with: prepend %
                val = '%' + (raw or '')
                op = 'ilike'
            else:
                val = raw
        except (ValueError, TypeError):
            val = raw
        return (self.field_id.name, op, val)


# ---------------------------------------------------------------------
# mv.report.group - one group-by row
# ---------------------------------------------------------------------
class MvReportGroup(models.Model):
    _name = 'mv.report.group'
    _description = 'Report Group-By'
    _order = 'sequence, id'

    report_id = fields.Many2one('mv.report', required=True, ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', required=True,
                               ondelete='cascade')
    field_name = fields.Char(related='field_id.name', store=True, readonly=True)
    # Phase 14 v4: dotted path from the report's base model.
    path = fields.Char(string='Path')
    node_id = fields.Many2one(
        'mv.report.type.node', string='From Node', ondelete='set null',
    )
    sequence = fields.Integer(default=10)


# ---------------------------------------------------------------------
# mv.report.sort - one sort row
# ---------------------------------------------------------------------
class MvReportSort(models.Model):
    _name = 'mv.report.sort'
    _description = 'Report Sort'
    _order = 'sequence, id'

    report_id = fields.Many2one('mv.report', required=True, ondelete='cascade')
    field_id = fields.Many2one('ir.model.fields', required=True,
                               ondelete='cascade')
    field_name = fields.Char(related='field_id.name', store=True, readonly=True)
    # Phase 14 v4: dotted path from the report's base model.
    path = fields.Char(string='Path')
    node_id = fields.Many2one(
        'mv.report.type.node', string='From Node', ondelete='set null',
    )
    direction = fields.Selection([('asc', 'Ascending'), ('desc', 'Descending')],
                                 string='Direction', default='asc', required=True)
    sequence = fields.Integer(default=10)
