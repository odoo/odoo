# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Materialize the versioned Thai translation sources into the OCA submodules.

The OCA repositories live under ``third_party/oca`` and are registered as git
submodules.  Any file added to them is *not* versioned by the superproject and
would be lost on a fresh clone.  This module keeps the authoritative ``.po``
files under ``sources/<module>/th.po`` (tracked by git) and copies them back to
``<oca_module>/i18n_extra/th.po`` on every server start, so that both
``model``/``model_terms`` entries and ``code`` entries keep working.
"""
import logging
from pathlib import Path

from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)

SOURCE_DIRNAME = "sources"
TARGET_SUBDIR = "i18n_extra"
PO_FILENAME = "th.po"


def _iter_sources():
    """Yield ``(module_name, source_po_path)`` for every versioned source."""
    base = Path(__file__).parent / SOURCE_DIRNAME
    if not base.is_dir():
        return
    for module_dir in sorted(base.iterdir()):
        source_po = module_dir / PO_FILENAME
        if module_dir.is_dir() and source_po.is_file():
            yield module_dir.name, source_po


def materialize():
    """Copy every source ``.po`` into its OCA module ``i18n_extra`` folder."""
    copied = 0
    for module_name, source_po in _iter_sources():
        module_path = get_module_path(module_name)
        if not module_path:
            _logger.warning(
                "Cannot materialize Thai translation: module %s is not available",
                module_name,
            )
            continue
        target_dir = Path(module_path) / TARGET_SUBDIR
        target_po = target_dir / PO_FILENAME
        data = source_po.read_bytes()
        if target_po.is_file() and target_po.read_bytes() == data:
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        target_po.write_bytes(data)
        copied += 1
    if copied:
        _logger.info("Materialized %d OCA Thai translation file(s)", copied)


def post_load():
    """Server-wide hook: refresh the OCA translation overlays at startup."""
    try:
        materialize()
    except Exception:  # noqa: BLE001 - never break the server bootstrap
        _logger.exception("Failed to materialize the OCA Thai translations")
