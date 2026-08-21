# -*- coding: utf-8 -*-
"""Phase 14 v4 - RPC methods for the Report Builder OWL client action.

The frontend (static/src/js/report_builder/) calls these methods to:
  - list Report Types available to the current user
  - fetch fields grouped by node (base + joined models) for a Report Type
  - load / save a report's columns / filters / groups / sorts
  - render a paged preview using the report's current spec
  - create a fresh report and clone / delete existing ones

v4 semantics: every column/filter/group/sort stores a PATH from the
base model, allowing fields to come from any joined node in the
Report Type. Preview execution walks the path with row-expansion for
one2many / many2many hops.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# Fields that are almost never useful in a report and just clutter
# the field picker. Hidden by default from report_get_fields.
#
# `id` is intentionally NOT hidden - users need to see the record
# id as a selectable column so reports can uniquely identify rows
# even when display_name / label values collide.
_HIDDEN_FIELDS = {
    'create_uid', 'create_date', 'write_uid', 'write_date',
    '__last_update', 'display_name',
    'message_ids', 'message_follower_ids', 'message_partner_ids',
    'message_attachment_count', 'message_has_error', 'message_needaction',
    'message_has_error_counter', 'message_needaction_counter',
    'message_has_sms_error', 'message_main_attachment_id',
    'activity_ids', 'activity_state', 'activity_user_id',
    'activity_type_id', 'activity_type_icon', 'activity_date_deadline',
    'activity_summary', 'activity_exception_decoration',
    'activity_exception_icon', 'website_message_ids',
    'rating_ids', 'has_message', 'access_token', 'access_url',
    'access_warning', 'my_activity_date_deadline',
}

# Relational fields ARE useful but shouldn't appear as terminal
# "columns" until we grow proper related-picker support. For now
# they're browsable but excluded.
_RELATIONAL_TERMINAL_HIDDEN = False  # keep them visible - they'll be m2o names


class MvReport(models.Model):
    _inherit = 'mv.report'

    # =====================================================================
    # Report Type RPCs
    # =====================================================================
    @api.model
    def report_type_get_all(self):
        """Return the list of Report Types visible to the current user."""
        rts = self.env['mv.report.type'].search([('active', '=', True)])
        return [{
            'id': rt.id,
            'name': rt.name,
            'description': rt.description or '',
            'base_model_id': rt.base_model_id.id,
            'base_model_tech': rt.base_model_id.model,
            'base_model_display': rt.base_model_id.name,
            'node_count': rt.node_count,
        } for rt in rts]

    @api.model
    def report_type_get_fields(self, report_type_id):
        """Return the fields for a Report Type, grouped by NODE.

        The response shape is:
            {
                'report_type': { id, name, base_model_id, ... },
                'nodes': [
                    {
                        'node_id': False,        # base
                        'label': 'Base — Deal',
                        'model_tech': 'mv.deal',
                        'path_prefix': '',
                        'relation_kind': None,   # base has no relation
                        'fields': [ { id, name, label, ttype, relation,
                                       path } ... ],
                    },
                    {
                        'node_id': 42,
                        'label': 'Advertiser',
                        'model_tech': 'mv.advertiser',
                        'path_prefix': 'advertiser_id',
                        'relation_kind': 'many2one',
                        'fields': [ ... ],
                    },
                    ...
                ],
            }

        Every field entry carries an absolute `path` (dotted access
        string from the base model). That path is what the Report
        Builder saves and the preview / run pipeline executes.
        """
        rt = self.env['mv.report.type'].browse(report_type_id).exists()
        if not rt:
            return {'report_type': None, 'nodes': []}

        # Base node -----------------------------------------------------
        nodes = [{
            'node_id': False,
            'label': _('Base — %s') % (rt.base_model_id.name or rt.base_model_id.model),
            'model_id': rt.base_model_id.id,
            'model_tech': rt.base_model_id.model,
            'path_prefix': '',
            'relation_kind': None,
            'fields': self._collect_model_fields(
                rt.base_model_id, path_prefix='', node_id=False,
            ),
        }]

        # Joined nodes --------------------------------------------------
        for node in rt.node_ids.sorted('sequence'):
            if not node.target_model_id:
                continue
            nodes.append({
                'node_id': node.id,
                'label': node.display_label or node.target_model_id.name,
                'model_id': node.target_model_id.id,
                'model_tech': node.target_model_id.model,
                'path_prefix': node.path_prefix or '',
                'relation_kind': node.relation_kind,
                'fields': self._collect_model_fields(
                    node.target_model_id,
                    path_prefix=node.path_prefix or '',
                    node_id=node.id,
                ),
            })

        return {
            'report_type': {
                'id': rt.id,
                'name': rt.name,
                'description': rt.description or '',
                'base_model_id': rt.base_model_id.id,
                'base_model_tech': rt.base_model_id.model,
                'base_model_display': rt.base_model_id.name,
            },
            'nodes': nodes,
        }

    @api.model
    def _collect_model_fields(self, model, path_prefix, node_id):
        """Return field metadata dicts for a model, filtered to the
        user-facing subset. Each entry carries an absolute `path`.

        For selection fields the entry also carries a `selection`
        list ([{value, label}, ...]) so the Report Builder can render
        a dropdown value input for filters on that field.
        """
        Field = self.env['ir.model.fields']
        raw = Field.search([
            ('model_id', '=', model.id),
            ('name', 'not in', list(_HIDDEN_FIELDS)),
        ], order='field_description, name')
        # Cache the model's runtime field map so we can pull selection
        # tuples per field. Retrieved once per model, not per field.
        try:
            model_obj = self.env[model.model]
        except KeyError:
            model_obj = None
        out = []
        for f in raw:
            fullpath = ('%s.%s' % (path_prefix, f.name)) if path_prefix else f.name
            entry = {
                'id': f.id,
                'name': f.name,
                'label': f.field_description or f.name,
                'ttype': f.ttype,
                'relation': f.relation or '',
                'path': fullpath,
                'node_id': node_id,
                'model_tech': model.model,
            }
            if f.ttype == 'selection':
                entry['selection'] = self._field_selection_options(
                    model_obj, f.name,
                )
            out.append(entry)
        return out

    @api.model
    def _field_selection_options(self, model_obj, field_name):
        """Return [{value, label}, ...] for a selection field. Handles
        both static list and callable selection specs."""
        if model_obj is None or field_name not in model_obj._fields:
            return []
        field = model_obj._fields[field_name]
        sel = getattr(field, 'selection', None) or []
        if callable(sel):
            try:
                sel = sel(model_obj)
            except Exception:
                return []
        try:
            return [{'value': v, 'label': str(l)} for v, l in sel]
        except (TypeError, ValueError):
            return []

    # =====================================================================
    # Report Load / Save
    # =====================================================================
    @api.model
    def report_load(self, report_id):
        """Load a report's full spec so the Builder can hydrate its state."""
        r = self.browse(report_id).exists()
        if not r:
            return None
        return {
            'id': r.id,
            'name': r.name,
            'description': r.description or '',
            'report_type_id': r.report_type_id.id if r.report_type_id else False,
            'report_type_name': r.report_type_id.name if r.report_type_id else '',
            'model_id': r.model_id.id if r.model_id else False,
            'model_tech': r.model_id.model if r.model_id else '',
            'is_public': r.is_public,
            'columns': [{
                'id': c.id,
                'field_id': c.field_id.id,
                'field_name': c.field_id.name,
                'label': c.field_label or c.field_id.field_description or c.field_id.name,
                'ttype': c.field_id.ttype,
                'path': c.path or c.field_id.name,
                'node_id': c.node_id.id if c.node_id else False,
                'aggregation': c.aggregation or 'none',
            } for c in r.column_ids.sorted('sequence')],
            'filters': [{
                'id': f.id,
                'field_id': f.field_id.id,
                'field_name': f.field_id.name,
                'label': f.field_id.field_description or f.field_id.name,
                'ttype': f.field_id.ttype,
                # selection options (if any) so the frontend can
                # render a proper <select> value input.
                # self.env doesn't have .get(); use `in` guard.
                'selection': self._field_selection_options(
                    (self.env[f.field_id.model_id.model]
                     if f.field_id.model_id.model in self.env else None),
                    f.field_id.name,
                ) if f.field_id.ttype == 'selection' else None,
                'path': f.path or f.field_id.name,
                'node_id': f.node_id.id if f.node_id else False,
                'operator': f.operator or '=',
                'value': f.value or '',
                'logical_op': f.logical_op or 'and',
            } for f in r.filter_ids.sorted('sequence')],
            'groups': [{
                'id': g.id,
                'field_id': g.field_id.id,
                'field_name': g.field_id.name,
                'label': g.field_id.field_description or g.field_id.name,
                'path': g.path or g.field_id.name,
                'node_id': g.node_id.id if g.node_id else False,
            } for g in r.group_ids.sorted('sequence')],
            'sorts': [{
                'id': s.id,
                'field_id': s.field_id.id,
                'field_name': s.field_id.name,
                'label': s.field_id.field_description or s.field_id.name,
                'path': s.path or s.field_id.name,
                'node_id': s.node_id.id if s.node_id else False,
                'direction': s.direction or 'asc',
            } for s in r.sort_ids.sorted('sequence')],
        }

    @api.model
    def report_save(self, report_id, payload):
        """Overwrite a report's spec with the given payload.
        Children are blown away + recreated (order preserved)."""
        r = self.browse(report_id).exists()
        if not r:
            raise UserError(_('Report %s not found') % report_id)

        # Header updates
        vals = {}
        if 'name' in payload:
            vals['name'] = payload['name']
        if 'description' in payload:
            vals['description'] = payload['description']
        if 'is_public' in payload:
            vals['is_public'] = bool(payload['is_public'])
        if payload.get('report_type_id'):
            vals['report_type_id'] = payload['report_type_id']
        if vals:
            r.write(vals)

        # Children: destroy + recreate in incoming order
        r.column_ids.unlink()
        r.filter_ids.unlink()
        r.group_ids.unlink()
        r.sort_ids.unlink()

        for i, c in enumerate(payload.get('columns') or []):
            self.env['mv.report.column'].create({
                'report_id': r.id,
                'field_id': c['field_id'],
                'field_label': c.get('label') or '',
                'path': c.get('path') or '',
                'node_id': c.get('node_id') or False,
                'aggregation': c.get('aggregation') or 'none',
                'sequence': i * 10,
            })
        for i, f in enumerate(payload.get('filters') or []):
            self.env['mv.report.filter'].create({
                'report_id': r.id,
                'field_id': f['field_id'],
                'path': f.get('path') or '',
                'node_id': f.get('node_id') or False,
                'operator': f.get('operator') or '=',
                'value': f.get('value') or '',
                'logical_op': f.get('logical_op') or 'and',
                'sequence': i * 10,
            })
        for i, g in enumerate(payload.get('groups') or []):
            self.env['mv.report.group'].create({
                'report_id': r.id,
                'field_id': g['field_id'],
                'path': g.get('path') or '',
                'node_id': g.get('node_id') or False,
                'sequence': i * 10,
            })
        for i, s in enumerate(payload.get('sorts') or []):
            self.env['mv.report.sort'].create({
                'report_id': r.id,
                'field_id': s['field_id'],
                'path': s.get('path') or '',
                'node_id': s.get('node_id') or False,
                'direction': s.get('direction') or 'asc',
                'sequence': i * 10,
            })
        return True

    # =====================================================================
    # Preview - walks paths + expands o2m/m2m
    # =====================================================================
    @api.model
    def report_preview(self, report_id, limit=20, offset=0):
        """Return a paged preview using the report's columns/filters/sorts.

        Row-expansion semantics:
          - The base rowset is filtered by the report's filter domain.
          - For each base row, we produce one report row PER combination
            of one2many/many2many hops. Base fields (m2o path or direct)
            duplicate across expanded rows.
        """
        r = self.browse(report_id).exists()
        if not r or not r.model_id:
            return {'columns': [], 'rows': [], 'total': 0,
                    'limit': limit, 'offset': offset}
        base_model = r.model_id.model
        try:
            BaseModel = self.env[base_model]
        except KeyError:
            return {'columns': [], 'rows': [], 'total': 0,
                    'limit': limit, 'offset': offset}

        # Preview columns metadata
        cols = []
        for c in r.column_ids.sorted('sequence'):
            path = c.path or (c.field_id.name if c.field_id else '')
            if not path:
                continue
            cols.append({
                'key': path,
                'label': c.field_label or c.field_id.field_description or c.field_id.name,
                'ttype': c.field_id.ttype,
            })

        # Base filter domain (path-aware) --------------------------------
        domain = r._build_domain()

        # Order for base query ------------------------------------------
        order_clauses = []
        for s in r.sort_ids.sorted('sequence'):
            spath = s.path or (s.field_id.name if s.field_id else '')
            # For ordering purposes, only base-model paths are safe for
            # SQL. Multi-hop paths are ignored here; sort happens in
            # Python after row expansion (below).
            if spath and '.' not in spath:
                dirn = 'desc' if s.direction == 'desc' else 'asc'
                order_clauses.append('%s %s' % (spath, dirn))
        order = ', '.join(order_clauses) if order_clauses else 'id desc'

        # Query the base model. We fetch MORE than the page limit so
        # row expansion can still fill a page even when base rows
        # produce multiple children each.
        overfetch = max(limit * 4, 100)
        base_records = BaseModel.search(domain, order=order, limit=overfetch)

        # Expand base records into report rows ---------------------------
        rows = self._expand_rows(base_records, cols)

        total = len(rows)
        page = rows[offset:offset + limit]
        return {
            'columns': cols,
            'rows': page,
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    @api.model
    def _expand_rows(self, base_records, cols):
        """Follow each column's path from each base record. If any
        column path traverses a one2many or many2many, the base row
        gets expanded into multiple report rows.

        This is a first-cut implementation: it detects the FIRST
        o2m/m2m along any column's path and pivots on that. Multiple
        independent o2m/m2m paths from the same base collapse into
        the cartesian product.
        """
        out = []
        for base in base_records:
            # For each column, resolve the value at the current row.
            # If a path segment is o2m/m2m, we'll cross-product later.
            # For now: collect (path, terminal_values_list, is_multi).
            row_frag = {'_id': 'base-%s' % base.id}
            multi_paths = {}  # path -> list of records at the multi hop
            simple = {}       # path -> scalar value

            for c in cols:
                path = c['key']
                parts = path.split('.')
                cur = base
                value = None
                is_multi = False
                traversal_ok = True
                for i, part in enumerate(parts):
                    if not cur:
                        value = ''
                        traversal_ok = False
                        break
                    # Recordset with 0 or many elems for o2m/m2m/m2o
                    if hasattr(cur, part):
                        nxt = getattr(cur, part)
                    else:
                        value = ''
                        traversal_ok = False
                        break
                    if hasattr(nxt, '_name') and len(nxt) != 1 and i < len(parts) - 1:
                        # We hit a one2many/many2many mid-path.
                        # Record the multi hop and stop here; the
                        # expansion pass below will re-resolve.
                        multi_paths.setdefault(
                            '.'.join(parts[:i + 1]), nxt,
                        )
                        value = None
                        is_multi = True
                        break
                    cur = nxt
                if not is_multi and traversal_ok:
                    # Final value could still be a recordset (m2o
                    # display name / m2m/o2m rendered as comma list).
                    if hasattr(cur, '_name'):
                        try:
                            value = ', '.join(cur.mapped('display_name'))
                        except Exception:
                            value = str(cur)
                    else:
                        value = cur if cur is not False else ''
                    simple[path] = value if value is not None else ''

            if not multi_paths:
                # Simple row, no expansion needed
                row = dict(row_frag)
                for c in cols:
                    row[c['key']] = simple.get(c['key'], '')
                out.append(row)
                continue

            # Expand: for each multi-hop path, take its children and
            # generate one row per child. If multiple multi-paths,
            # cartesian product.
            multi_items = list(multi_paths.items())
            expanded = [{}]
            for path, recs in multi_items:
                new_expanded = []
                child_list = list(recs) if recs else [None]
                for base_ctx in expanded:
                    for child in child_list:
                        ctx = dict(base_ctx)
                        ctx[path] = child
                        new_expanded.append(ctx)
                expanded = new_expanded

            for ctx in expanded:
                row = {'_id': '%s-%s' % (
                    row_frag['_id'],
                    '-'.join('%s:%s' % (p, (c.id if c else 'nul'))
                             for p, c in ctx.items()),
                )}
                for c in cols:
                    path = c['key']
                    if path in simple:
                        row[path] = simple[path]
                        continue
                    # Re-resolve path using the ctx multi-hop values
                    parts = path.split('.')
                    cur = base
                    idx = 0
                    val = ''
                    while idx < len(parts):
                        prefix = '.'.join(parts[:idx + 1])
                        if prefix in ctx:
                            cur = ctx[prefix]
                            idx += 1
                            continue
                        if cur is None:
                            val = ''
                            break
                        if hasattr(cur, parts[idx]):
                            cur = getattr(cur, parts[idx])
                        else:
                            val = ''
                            cur = None
                            break
                        idx += 1
                    if cur is None or cur is False:
                        val = ''
                    elif hasattr(cur, '_name'):
                        try:
                            val = ', '.join(cur.mapped('display_name'))
                        except Exception:
                            val = str(cur)
                    else:
                        val = cur
                    row[path] = val if val is not None else ''
                out.append(row)
        return out

    # =====================================================================
    # Report management
    # =====================================================================
    @api.model
    def report_create_blank(self, report_type_id=None):
        vals = {'name': _('New Report')}
        if report_type_id:
            vals['report_type_id'] = report_type_id
        return self.create(vals).id

    def report_clone(self):
        self.ensure_one()
        clone = self.copy({'name': _('%s (copy)') % self.name})
        return clone.id

    def report_delete(self):
        self.ensure_one()
        self.unlink()
        return True


class MvReportFilter(models.Model):
    _inherit = 'mv.report.filter'

    def _to_domain_term(self):
        """Convert to a domain tuple. Use the stored path if present
        (so filters on joined-model fields work), else fall back to
        the terminal field name.

        Empty-value semantics: if the user hasn't typed a value yet
        (raw == ''), the filter row is INCOMPLETE and should NOT
        contribute a domain term. Otherwise Odoo's date/datetime
        domain optimizer crashes trying to parse '' as an ISO date.
        Returning None here silently drops the filter from the
        composed domain, which matches user intent (empty = no
        constraint) and gives the planner a chance to fill it in.

        Note: Odoo's ORM handles dotted paths natively for m2o hops.
        For o2m/m2m, the domain becomes an ANY-match condition (any
        related row matching the filter includes the base row).
        """
        self.ensure_one()
        if not self.field_id:
            return None
        path = self.path or self.field_id.name
        op = self.operator or '='
        raw = self.value or ''
        ttype = self.field_id.ttype
        # Incomplete filter (no value) - skip. Special-case: boolean
        # filters treat '' as False intentionally, so keep them.
        if not raw and ttype != 'boolean':
            return None
        # Malformed date/datetime: Odoo's domain optimizer aggressively
        # tries to parse the value as an ISO date and crashes on
        # garbage like '2' or 'not-a-date'. Probe the format here and
        # drop the filter row rather than passing garbage through.
        if ttype in ('date', 'datetime'):
            from datetime import date as _d, datetime as _dt
            try:
                if ttype == 'date':
                    _d.fromisoformat(raw)
                else:
                    # datetime.fromisoformat accepts 'YYYY-MM-DD' too,
                    # so it also validates dates-typed-as-datetime.
                    _dt.fromisoformat(raw)
            except (ValueError, TypeError):
                return None
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
                val = (raw or '') + '%'
                op = 'ilike'
            elif op == 'like%':
                val = '%' + (raw or '')
                op = 'ilike'
            else:
                val = raw
        except (ValueError, TypeError):
            val = raw
        return (path, op, val)
