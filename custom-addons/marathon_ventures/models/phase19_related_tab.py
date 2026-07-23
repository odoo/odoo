# -*- coding: utf-8 -*-
"""Phase 19 - Related tab (Salesforce-style dynamic relationships pane).

Every form view backed by an `mv.*` model gets an extra "Related"
notebook page injected client-side. This helper model exposes the
single RPC that page calls to fetch the data.

The tab discovers all One2many / Many2many relationships on the
active record's model, respects the user's ACL on both the parent
and each related model, and returns:

    [
        {
            'field_name':  'schedule_ids',
            'label':       'Schedules',
            'type':        'one2many',
            'comodel':     'mv.schedules',
            'comodel_label': 'Schedules',
            'inverse_name': 'deal_parent',   # only for O2M
            'count':       52,
            'accessible':  True,
            'preview':     [{'id': 1, 'display_name': 'Sched-001'}, ...],
        },
        ...
    ]

Fields deliberately excluded from discovery:
  * message_ids / activity_ids / message_follower_ids etc.
    (mail.thread / mail.activity plumbing - already shown in chatter)
  * Fields the user cannot read on the related model
  * Related fields (they're just views onto other models' data)
"""
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


# Field names we never want to show as a Related section - they're
# framework plumbing rather than business relationships.
_HIDDEN_FIELDS = frozenset([
    'message_ids', 'message_follower_ids', 'message_partner_ids',
    'message_channel_ids', 'message_main_attachment_id',
    'activity_ids', 'activity_calendar_event_id',
    'website_message_ids', 'rating_ids',
    # Attachment plumbing
    '__last_update',
])

# Comodels whose relations are noise on the Related tab (Odoo core
# framework internals rather than business objects).
_HIDDEN_COMODELS = frozenset([
    'mail.message', 'mail.followers', 'mail.activity',
    'ir.attachment.link',
    'bus.presence',
])

_MAX_PREVIEW = 2   # rows to show under each section header


class MvRelated(models.AbstractModel):
    _name = 'mv.related'
    _description = 'Related tab data provider'

    @api.model
    def related_specs(self, model, res_id, columns=None):
        """Return a list of related-section dicts for the given record.

        `columns` is an optional dict shaped like:

            {"mv.deal":      ["name", "length"],
             "mv.schedules": ["name", "rate", "week", "max_per_day"]}

        Coming from the frontend's RELATED_TAB_COLUMNS map. When a
        section's comodel is listed there, the given fields are
        fetched + formatted as extra label/value pairs under each
        preview record's display_name link. Comodels NOT listed
        keep the default rendering (display_name only).

        Empty list for unknown models, unsaved records, or when the
        caller lacks read on the parent record itself.
        """
        if not model or not res_id:
            return []
        # Only expose our own models. Prevents any accidental use of
        # this RPC against core models.
        if not model.startswith('mv.'):
            return []
        if model not in self.env:
            return []
        Parent = self.env[model]
        if not Parent.has_access('read'):
            return []
        rec = Parent.browse(int(res_id))
        if not rec.exists():
            return []
        try:
            rec.check_access('read')
        except Exception:
            return []

        columns = columns or {}
        out = []
        # Deterministic ordering by field label so the UI is stable.
        field_items = sorted(
            Parent._fields.items(),
            key=lambda kv: (kv[1].string or kv[0]).lower(),
        )
        for fname, field in field_items:
            if field.type not in ('one2many', 'many2many'):
                continue
            if fname in _HIDDEN_FIELDS:
                continue
            if not getattr(field, 'store', True) and field.type == 'many2many':
                # Skip non-stored M2M (usually helpers)
                continue
            comodel = field.comodel_name
            if not comodel or comodel not in self.env:
                continue
            if comodel in _HIDDEN_COMODELS:
                continue
            Co = self.env[comodel]
            spec = {
                'field_name': fname,
                'label': field.string or fname,
                'type': field.type,
                'comodel': comodel,
                'comodel_label': Co._description or comodel,
                'inverse_name': getattr(field, 'inverse_name', False) or False,
                'count': 0,
                'accessible': True,
                'columns': [],
                'preview': [],
            }
            # ACL: hide sections the user cannot read.
            if not Co.has_access('read'):
                spec['accessible'] = False
                out.append(spec)
                continue
            # Fetch the related recordset via the field itself so
            # record rules on the parent's relation are respected.
            try:
                related_recs = rec[fname]
            except Exception:
                continue
            # Column list from the JS map, filtered to only fields
            # that actually exist on the comodel. Empty -> just
            # display_name (the classic Salesforce look).
            col_names = []
            for cn in (columns.get(comodel) or []):
                if cn in Co._fields:
                    col_names.append(cn)
            if not col_names:
                col_names = ['display_name']
            spec['columns'] = [
                {
                    'name': n,
                    'label': (
                        'Name' if n == 'display_name'
                        else (Co._fields[n].string or n)
                    ),
                }
                for n in col_names
            ]
            spec['count'] = len(related_recs)
            spec['preview'] = self._collect_preview(related_recs, col_names)
            out.append(spec)
        return out

    def _collect_preview(self, recs, col_names):
        """Return up to _MAX_PREVIEW row dicts. Each row has 'id' and
        'display_name' plus every extra column formatted as a string.
        Errors on individual rows are logged then skipped so one bad
        record can't hide the whole section."""
        _logger.info(
            "[Related] _collect_preview called: comodel=%s recs.count=%s "
            "recs.ids=%s col_names=%s",
            (recs._name if recs else '?'),
            len(recs) if recs else 0,
            list(recs.ids)[:_MAX_PREVIEW] if recs else [],
            col_names,
        )
        out = []
        for r in recs[:_MAX_PREVIEW]:
            try:
                # display_name is a compute that can raise AccessError
                # for row-level record rules. Read it defensively so
                # one restricted row doesn't drop the entire section.
                try:
                    dn = r.display_name
                except Exception as e:
                    _logger.warning(
                        "[Related] display_name on %s#%s failed: %s",
                        r._name, r.id, e,
                    )
                    dn = None
                row = {
                    'id': r.id,
                    'display_name': dn or ('#%d' % r.id),
                }
                for cname in col_names:
                    if cname == 'display_name':
                        continue
                    try:
                        v = r[cname]
                    except Exception as e:
                        _logger.warning(
                            "[Related] field %s on %s#%s failed: %s",
                            cname, r._name, r.id, e,
                        )
                        v = False
                    _logger.info(
                        "[Related]   read %s#%s.%s = %r (type=%s)",
                        r._name, r.id, cname, v,
                        r._fields[cname].type if cname in r._fields else '?',
                    )
                    try:
                        row[cname] = _format_cell(v, r._fields.get(cname))
                    except Exception as e:
                        _logger.warning(
                            "[Related] format %s=%r on %s#%s failed: %s",
                            cname, v, r._name, r.id, e,
                        )
                        row[cname] = ''
                out.append(row)
            except Exception as e:
                # Log so we can see WHY a preview row got dropped.
                # Guard the log call itself - if r is a broken proxy
                # even reading its _name / id could raise, and that
                # would silently swallow the real exception.
                try:
                    _logger.exception(
                        "[Related] skipping preview record: %s", e,
                    )
                except Exception:
                    pass
                continue
        _logger.info(
            "[Related] _collect_preview returning %d row(s)",
            len(out),
        )
        return out

# =====================================================================
# Auto-inject the "Related" notebook page into every mv.* form view.
#
# Hook: BaseModel._get_view is Odoo 19's central view-loading path.
# We call super() to fetch the compiled arch, then walk it if we
# are on a form view for an mv.* model. We look for a <sheet>, find
# (or create) its trailing <notebook>, and append one <page> with
# our widget bound to the record's `id` field.
#
# The widget itself (mv_related_tab, registered in mv_related_tab.js)
# takes it from there - fetching related_specs() on mount + on
# record change.
# =====================================================================
from lxml import etree


class BaseModelWithRelatedTab(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)
        try:
            if view_type != 'form':
                return arch, view
            if not self._name or not self._name.startswith('mv.'):
                return arch, view
            # Some transient / wizard models get injected too - but
            # the widget is defensive (fires nothing if resId is
            # falsy) so this is safe.
            arch = _inject_related_page(arch)
        except Exception:
            # NEVER let a view injection error break the caller.
            # Odoo's form load has to succeed even if our helper
            # can't attach itself.
            pass
        return arch, view


def _inject_related_page(arch):
    """Take a form-view arch (etree Element) and append a Related
    notebook page. Idempotent - if a page with our marker name
    already exists we don't add a second one."""
    if arch is None:
        return arch
    if arch.tag != 'form':
        return arch
    # Idempotency guard.
    for page in arch.iter('page'):
        if page.get('name') == 'mv_related_tab':
            return arch
    # Find sheet + notebook (create notebook if missing).
    sheet = arch.find('.//sheet')
    if sheet is None:
        # Some forms don't use <sheet> - inject at the form's tail.
        parent = arch
    else:
        parent = sheet
    notebook = parent.find('./notebook')
    if notebook is None:
        # Also check nested one-level down (some forms nest oddly).
        notebook = parent.find('.//notebook')
    if notebook is None:
        # No notebook at all - build one at the tail of the parent
        # so our page has somewhere to live.
        notebook = etree.SubElement(parent, 'notebook')
    page = etree.SubElement(notebook, 'page', {
        'string': 'Related',
        'name': 'mv_related_tab',
    })
    etree.SubElement(page, 'field', {
        'name': 'id',
        'widget': 'mv_related_tab',
        'nolabel': '1',
    })
    return arch



def _format_cell(v, field):
    """Turn a scalar / relational field value into a display string.
    Mirrors how Odoo renders read() output in a list view."""
    if v is False or v is None:
        return ''
    if isinstance(v, bool):
        return 'Yes' if v else 'No'
    try:
        if field is not None and field.type == 'many2one':
            return v.display_name if v else ''
        if field is not None and field.type == 'selection':
            if callable(field.selection):
                return str(v)
            sel = dict(field.selection or [])
            return sel.get(v, v) or str(v)
        if field is not None and field.type in ('one2many', 'many2many'):
            return ', '.join(
                (r.display_name or ('#%d' % r.id)) for r in v[:3]
            )
        if hasattr(v, 'isoformat'):
            return v.isoformat()
    except Exception:
        pass
    return str(v)
