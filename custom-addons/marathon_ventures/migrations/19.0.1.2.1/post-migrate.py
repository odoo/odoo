# -*- coding: utf-8 -*-
"""One-time fix: unarchive mv.split rows that were ghost-archived by
the broken `_compute_active`.

Before this migration:
  * `mv.split.active` was a stored compute that unconditionally set
    the field to False.
  * Odoo treats `active=False` as archived and hides the record from
    default searches.
  * Result: every Split created via the form silently became invisible
    on save, giving the appearance that Save was broken.

The compute has been replaced with a plain Boolean default=True in
the model. This migration flips every existing row that was left in
the archived state by the buggy compute. We use direct SQL so we
don't accidentally trigger any new compute chain.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute(
        "UPDATE mv_split SET active = TRUE WHERE active = FALSE OR active IS NULL"
    )
    _logger.info(
        "mv.split: unarchived %d row(s) previously ghost-archived by "
        "the broken _compute_active.",
        cr.rowcount,
    )
