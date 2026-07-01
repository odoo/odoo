# -*- coding: utf-8 -*-
"""Phase 14 v3 - RPC endpoints powering the OWL Report Builder.

Kept in its own file so the main model definitions stay focused on
the schema. Every method here is @api.model so the front-end can
call it without pre-existing recordsets.
"""
from odoo import models, api, fields, _
from odoo.exceptions import UserError


class MvReportRpc(models.Model):
    _name = 'mv.report'
    _inherit = 'mv.report'

    # ---- Model picker (left sidebar) --------------------------------
    @api.model
    def report_get_models(self):
        """List every mv.* model the planner can build a report against,
        with a rough field count for the sidebar."""
        IrModel = self.env['ir.model'].sudo()
        IrField = self.env['ir.model.fields'].sudo()
        recs = IrModel.search([('model', '=like', 'mv.%')], order='name')
        out = []
        for m in recs:
            count = IrField.search_count([
                ('model_id', '=', m.id), ('store', '=', True),
            ])
            out.append({
                'id': m.id,
                'name': m.name,
                'tech': m.model,
                'field_count': count,
            })
        return out

    @api.model
    def report_get_fields(self, model_id):
        """Return fields for one model, sorted by label. Includes the
        field type so the UI can render appropriate filter widgets."""
        if not model_id:
            return []
        rows = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', model_id),
            ('store', '=', True),
        ], order='field_description')
        return [{
            'id': f.id,
            'name': f.name,
            'label': f.field_description or f.name,
            'ttype': f.ttype,
            'relation': f.relation or '',
        } for f in rows]

    @api.model
    def report_get_related_fields(self, m2o_field_id):
        """Given a Many2one field's id, return the target model's
        fields so the planner can drill into related data."""
        f = self.env['ir.model.fields'].sudo().browse(m2o_field_id)
        if not f.exists() or f.ttype != 'many2one' or not f.relation:
            return []
        target = self.env['ir.model'].sudo().search(
            [('model', '=', f.relation)], limit=1,
        )
        if not target:
            return []
        return self.report_get_fields(target.id)

    # ---- Saved-report load / save ----------------------------------
    @api.model
    def report_load(self, report_id):
        """Return the full saved state of a report - everything the
        OWL component needs to rehydrate."""
        rec = self.browse(report_id)
        if not rec.exists():
            return None
        return {
            'id': rec.id,
            'name': rec.name or '',
            'description': rec.description or '',
            'model_id': rec.model_id.id,
            'model_name': rec.model_id.name,
            'model_tech': rec.model_id.model,
            'is_public': rec.is_public,
            'columns': [{
                'id': c.id,
                'field_id': c.field_id.id,
                'field_name': c.field_id.name,
                'label': c.field_label or c.field_id.field_description,
                'ttype': c.field_id.ttype,
                'sequence': c.sequence,
                'aggregation': c.aggregation,
            } for c in rec.column_ids.sorted('sequence')],
            'filters': [{
                'id': f.id,
                'field_id': f.field_id.id,
                'field_name': f.field_id.name,
                'label': f.field_id.field_description,
                'ttype': f.field_id.ttype,
                'operator': f.operator,
                'value': f.value or '',
                'sequence': f.sequence,
                'logical_op': f.logical_op,
            } for f in rec.filter_ids.sorted('sequence')],
            'groups': [{
                'id': g.id,
                'field_id': g.field_id.id,
                'field_name': g.field_id.name,
                'label': g.field_id.field_description,
                'sequence': g.sequence,
            } for g in rec.group_ids.sorted('sequence')],
            'sorts': [{
                'id': s.id,
                'field_id': s.field_id.id,
                'field_name': s.field_id.name,
                'label': s.field_id.field_description,
                'direction': s.direction,
                'sequence': s.sequence,
            } for s in rec.sort_ids.sorted('sequence')],
        }

    @api.model
    def report_save(self, report_id, payload):
        """Persist the full report definition. Replaces child rows so
        the planner sees exactly what they configured in the UI."""
        rec = self.browse(report_id)
        if not rec.exists():
            return False
        payload = payload or {}
        head = {}
        for k in ('name', 'description', 'is_public'):
            if k in payload:
                head[k] = payload[k]
        if 'model_id' in payload and payload['model_id'] != rec.model_id.id:
            head['model_id'] = payload['model_id']
        if head:
            rec.write(head)
        # --- Children: blow away + recreate (small N, simple semantics)
        rec.column_ids.unlink()
        for i, c in enumerate(payload.get('columns', [])):
            self.env['mv.report.column'].create({
                'report_id': rec.id,
                'field_id': c['field_id'],
                'field_label': c.get('label') or False,
                'sequence': i * 10,
                'aggregation': c.get('aggregation') or 'none',
            })
        rec.filter_ids.unlink()
        for i, f in enumerate(payload.get('filters', [])):
            self.env['mv.report.filter'].create({
                'report_id': rec.id,
                'field_id': f['field_id'],
                'operator': f.get('operator') or '=',
                'value': f.get('value') or '',
                'sequence': i * 10,
                'logical_op': f.get('logical_op') or 'and',
            })
        rec.group_ids.unlink()
        for i, g in enumerate(payload.get('groups', [])):
            self.env['mv.report.group'].create({
                'report_id': rec.id,
                'field_id': g['field_id'],
                'sequence': i * 10,
            })
        rec.sort_ids.unlink()
        for i, s in enumerate(payload.get('sorts', [])):
            self.env['mv.report.sort'].create({
                'report_id': rec.id,
                'field_id': s['field_id'],
                'direction': s.get('direction') or 'asc',
                'sequence': i * 10,
            })
        return True

    # ---- Preview ----------------------------------------------------
    @api.model
    def report_preview(self, report_id, limit=20, offset=0):
        """Return up to `limit` rows starting at `offset`, plus the
        column metadata + total row count. Respects ACL + record rules
        by routing through the user-level env (not sudo)."""
        rec = self.browse(report_id)
        if not rec.exists() or not rec.model_id:
            return {'columns': [], 'rows': [], 'total': 0, 'limit': limit, 'offset': offset}
        Target = self.env[rec.model_id.model]
        domain = rec._build_domain()
        # Sort
        order_terms = []
        for s in rec.sort_ids.sorted('sequence'):
            order_terms.append(f"{s.field_id.name} {s.direction}")
        order = ', '.join(order_terms) or None
        # Columns
        columns = []
        for c in rec.column_ids.sorted('sequence'):
            columns.append({
                'key': c.field_id.name,
                'label': c.field_label or c.field_id.field_description,
                'ttype': c.field_id.ttype,
                'aggregation': c.aggregation,
            })
        if not columns:
            return {
                'columns': [], 'rows': [],
                'total': Target.search_count(domain),
                'limit': limit, 'offset': offset,
            }
        # Fetch
        try:
            total = Target.search_count(domain)
            recs = Target.search(domain, limit=limit, offset=offset, order=order)
        except Exception as e:
            return {'columns': columns, 'rows': [], 'total': 0,
                    'limit': limit, 'offset': offset, 'error': str(e)}
        rows = []
        for r in recs:
            row = {'_id': r.id}
            for col in columns:
                val = r[col['key']]
                if hasattr(val, '_name'):
                    val = val.display_name if val else ''
                if val is False or val is None:
                    val = ''
                row[col['key']] = val
            rows.append(row)
        return {
            'columns': columns, 'rows': rows, 'total': total,
            'limit': limit, 'offset': offset,
        }

    # ---- CRUD helpers used by the UI -------------------------------
    @api.model
    def report_create_blank(self):
        """Spawn a new empty report and return its id. The OWL action
        opens it immediately so the planner starts configuring."""
        rec = self.create({
            'name': _('New Report'),
            'model_id': self.env['ir.model'].sudo().search(
                [('model', '=', 'mv.deal')], limit=1,
            ).id or False,
        })
        return rec.id

    @api.model
    def report_clone(self, report_id):
        src = self.browse(report_id)
        if not src.exists():
            return False
        dup = src.copy(default={'name': (src.name or '') + ' (Copy)'})
        return dup.id

    @api.model
    def report_delete(self, report_id):
        rec = self.browse(report_id)
        if rec.exists():
            rec.unlink()
        return True
