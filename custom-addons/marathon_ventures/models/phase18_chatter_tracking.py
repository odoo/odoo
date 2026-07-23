# -*- coding: utf-8 -*-
"""Phase 18 - Automatic chatter tracking on every mv.* model field.

Odoo's chatter only logs field changes for fields whose declaration
includes `tracking=True`. Manually adding that to hundreds of fields
across every mv.* model is impractical, so we do it at registry
setup time: for every model whose name starts with `mv.`, walk
every scalar stored field and flip `tracking = True`. The chatter
then automatically writes a "Field X: old -> new" entry to the
record's log every time it's saved.

Explicitly EXCLUDED:

  * Standard audit fields (create_uid/create_date/write_uid/
    write_date) - Odoo already stamps these, tracking them would
    be noisy nonsense on every write.
  * Complex field types (binary / html / json / one2many /
    many2many) - the tracking message is either huge or
    meaningless. Many2one IS tracked (displays 'X -> Y' with
    display_names).
  * Compute fields WITHOUT store=True - nothing to write anyway.

Runs at module install/upgrade via mail.thread._register_hook,
which fires once per model class at registry finalisation - so
this happens automatically after every server restart, not just
on install/upgrade.
"""
from odoo import models


# Field types worth logging in the chatter. Complex types are
# skipped because their tracking message is either huge (binary,
# html) or meaningless (json). One2many/Many2many changes are
# usually driven by the related record's own chatter anyway.
_TRACKABLE_TYPES = frozenset([
    'char', 'text',
    'integer', 'float', 'monetary',
    'boolean',
    'date', 'datetime',
    'selection',
    'many2one',
])

# Fields whose changes we DON'T want to see (already logged
# elsewhere by Odoo, or noise-only).
_EXCLUDED_FIELD_NAMES = frozenset([
    'create_uid', 'create_date',
    'write_uid', 'write_date',
    '__last_update', 'display_name',
    'sf_external_id',   # migration id, changes rarely + not user-facing
])


class MvChatterAutoTracking(models.AbstractModel):
    _inherit = 'mail.thread'

    def _register_hook(self):
        """Flip tracking=True on all scalar fields of mv.* models.
        Runs once per model class at registry finalisation.
        """
        res = super()._register_hook()
        model_name = self._name or ''
        if model_name.startswith('mv.'):
            for fname, field in self._fields.items():
                if fname in _EXCLUDED_FIELD_NAMES:
                    continue
                if not getattr(field, 'store', False):
                    continue
                if field.type not in _TRACKABLE_TYPES:
                    continue
                if getattr(field, 'tracking', False):
                    continue
                # Field descriptors are shared across model
                # subclasses, so setting the attr flips tracking
                # for this field everywhere it appears.
                field.tracking = True
        return res
