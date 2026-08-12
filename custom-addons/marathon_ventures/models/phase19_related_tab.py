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


# Sections that expose a "New <Label>" button in the Related tab.
# Kept as an explicit (parent_model, comodel) whitelist so quick-
# create only shows up where it's genuinely helpful; every other
# section renders as read-only preview + View All. Extend this set
# to enable quick-create on more sections.
_CREATE_ENABLED_PAIRS = {
    ('mv.traffic', 'mv.split'),
}


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
    def related_specs(self, model, res_id, config=None):
        """Return a list of Related-section dicts for the given record.

        `config` is a nested dict of the shape:

            {"<parent.model>": {"<comodel.name>": ["<col>", ...],
                                 ...},
             ...}

        Only comodels explicitly listed under the parent get a section
        (explicit opt-in). Empty list when the parent isn't in the
        config, when the record is unsaved, or when the caller can't
        read the parent.

        Each requested comodel is reached in this order:
          1. A One2many / Many2many field on the parent whose
             comodel_name matches - use it (records via `parent[field]`).
          2. A Many2one field on the COMODEL pointing back to the
             parent - treat it as a virtual One2many and fetch via
             `Co.search([(inv, '=', parent.id)])`. This is how
             Deal -> Traffic and Schedule -> SpotData work: there is
             NO forward O2M, only an inverse M2O.
          3. If neither exists, mark the section as accessible=False
             so the UI shows an "Access denied" placeholder rather
             than silently swallowing the config entry.
        """
        if not model or not res_id:
            return []
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

        config = config or {}
        per_model = config.get(model) or {}
        if not per_model:
            # Explicit opt-in: no config for this parent -> no sections.
            return []

        out = []
        for comodel, col_names_raw in per_model.items():
            spec = self._build_related_section(
                rec, comodel, col_names_raw or [],
            )
            if spec is not None:
                out.append(spec)
        return out

    def _build_related_section(self, rec, comodel, col_names_raw):
        """Build one section dict for the given (parent record, comodel).
        Returns None only if the comodel doesn't exist in the registry.
        """
        if comodel not in self.env:
            _logger.warning(
                "[Related] comodel %r not in registry", comodel,
            )
            return None
        Co = self.env[comodel]
        Parent = rec
        parent_model = Parent._name

        # ------- Special case: ir.attachment is polymorphic --------
        # It uses res_model/res_id instead of a real inverse M2O, so
        # neither of the two standard discovery paths finds it. We
        # short-circuit and search directly by res_model/res_id, which
        # returns every attachment owned by this parent (uploads from
        # the Related tab's Attach File button + chatter attachments +
        # anything else with res_model set to the parent).
        if comodel == 'ir.attachment':
            spec = {
                'field_name': False,
                'label': 'Notes & Attachments',
                'type': 'polymorphic',
                'comodel': comodel,
                'comodel_label': Co._description or comodel,
                'inverse_name': 'res_id',
                'count': 0,
                'accessible': True,
                'columns': [],
                'preview': [],
                # UI flag - frontend uses this to render the Attach
                # File button and to filter uploads to this parent.
                'supports_upload': True,
                'upload_res_model': parent_model,
                'upload_res_id': rec.id,
            }
            if not Co.has_access('read'):
                spec['accessible'] = False
                return spec
            try:
                related_recs = Co.search([
                    ('res_model', '=', parent_model),
                    ('res_id', '=', rec.id),
                ], order='create_date desc, id desc')
            except Exception as e:
                _logger.warning(
                    "[Related] fetch ir.attachment for %s#%s failed: %s",
                    parent_model, rec.id, e,
                )
                spec['accessible'] = False
                return spec
            col_names = []
            for cn in col_names_raw:
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
            return spec

        # ------- Locate the relationship path (direct or inverse) -------
        field_name = False
        inverse_name = False
        field_type = 'one2many'
        label = Co._description or comodel

        direct = self._find_direct_relation(Parent, comodel)
        if direct:
            fname, field = direct
            field_name = fname
            inverse_name = getattr(field, 'inverse_name', False) or False
            field_type = field.type
            label = field.string or fname
        else:
            inv = self._find_inverse_m2o(Co, parent_model)
            if inv:
                inverse_name = inv.name
                field_type = 'one2many'   # virtual
                label = Co._description or comodel

        spec = {
            'field_name': field_name,
            'label': label,
            'type': field_type,
            'comodel': comodel,
            'comodel_label': Co._description or comodel,
            'inverse_name': inverse_name,
            'count': 0,
            'accessible': True,
            'columns': [],
            'preview': [],
            'supports_upload': False,
            # Only whitelisted (parent, comodel) pairs render the
            # "New <Label>" button (see _CREATE_ENABLED_PAIRS at the
            # top of this module). Everything else is preview-only.
            'supports_create': (
                (parent_model, comodel) in _CREATE_ENABLED_PAIRS
                and bool(inverse_name or field_name)
            ),
            'parent_model': parent_model,
            'parent_id': rec.id,
        }

        # No relationship found at all -> flag as inaccessible with a
        # visible label so the admin knows the config entry is broken.
        if not field_name and not inverse_name:
            _logger.warning(
                "[Related] no path from %s to %s (neither direct "
                "O2M/M2M nor inverse M2O). Check RELATED_TAB_CONFIG.",
                parent_model, comodel,
            )
            spec['accessible'] = False
            return spec

        # ------- ACL on the comodel itself -------
        if not Co.has_access('read'):
            spec['accessible'] = False
            return spec

        # ------- Fetch related recordset -------
        try:
            if field_name:
                related_recs = rec[field_name]
            else:
                related_recs = Co.search([(inverse_name, '=', rec.id)])
        except Exception as e:
            _logger.warning(
                "[Related] fetch %s from %s#%s via %s failed: %s",
                comodel, parent_model, rec.id,
                (field_name or 'inverse=' + inverse_name), e,
            )
            spec['accessible'] = False
            return spec

        # ------- Column list: filter to actually-existing fields -------
        col_names = []
        for cn in col_names_raw:
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
        return spec

    def _find_direct_relation(self, Parent, comodel):
        """Return (field_name, field) for the first O2M or M2M field on
        Parent whose comodel matches. None if none found."""
        for fname, field in Parent._fields.items():
            if fname in _HIDDEN_FIELDS:
                continue
            if field.type not in ('one2many', 'many2many'):
                continue
            if field.comodel_name != comodel:
                continue
            if not getattr(field, 'store', True) and field.type == 'many2many':
                continue
            return fname, field
        return None

    def _find_inverse_m2o(self, Co, parent_model):
        """Return the Many2one field on Co that points at parent_model.
        None if the comodel has no back-reference. If multiple exist,
        the first stored one wins (deterministic per _fields order)."""
        for cname, cfield in Co._fields.items():
            if cfield.type != 'many2one':
                continue
            if cfield.comodel_name != parent_model:
                continue
            if not getattr(cfield, 'store', True):
                continue
            return cfield
        return None

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
