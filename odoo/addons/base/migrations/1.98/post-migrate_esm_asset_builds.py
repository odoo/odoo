"""Every generated ESM file gets an owner: the build that wrote it.

Until now nothing recorded which build of a bundle was current, and every rule
that decided what to keep guessed it from urls and names -- which deleted the
page-scoped variant a bundle's plain build shares its name with, and never
collected a uniquely named esbuild chunk. `ir.asset.build` records it; a file is
kept while a build that is current, or superseded less than the grace ago, owns
its directory.

The files already stored predate that record. Each directory becomes one build,
superseded now, under a variant of its own: pages already in browsers keep being
served for one grace period, the first render of every bundle publishes a
current build beside them, and the sweep collects them afterwards. Nothing is
recompiled by the upgrade itself.

The by-source pointers (`/web/assets/esm/by-source/...`) are deleted: the build
carries the source key they held. A process that finds none compiles once.
"""

import logging
from collections import defaultdict

from odoo import api, fields
from odoo.api import SUPERUSER_ID
from odoo.fields import Domain

from odoo.addons.base.models.ir_asset_build import (
    ESM_URL_PREFIX,
    build_directory,
    build_fingerprint,
)
from odoo.addons.base.models.ir_attachment_assets import (
    ESM_BRIDGES_URL_PREFIX,
    ESM_LIBS_URL_PREFIX,
)

_logger = logging.getLogger(__name__)


def _kind_and_bundle(directory: str, names: list[str]) -> tuple[str, str]:
    if directory.startswith(ESM_LIBS_URL_PREFIX):
        return "lib", "esm.libs"
    if "group.meta.json" in names or any(n.startswith("chunk-") for n in names):
        return "group", "legacy"
    code = sorted(n.removesuffix(".esm.js") for n in names if n.endswith(".esm.js"))
    if code and code[0].endswith(".templates"):
        return "templates", code[0]
    return "bundle", code[0] if code else "legacy"


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    IrAttachment = env["ir.attachment"]
    pointers = IrAttachment.search(
        IrAttachment._get_domain_generated_assets(
            url_pattern=f"{ESM_URL_PREFIX}by-source/%"
        )
    )
    pointer_count = len(pointers)
    pointers.unlink()

    rows = IrAttachment.search_fetch(
        IrAttachment._get_domain_generated_assets()
        & Domain.OR(
            [
                [("url", "=like", f"{ESM_URL_PREFIX}%")],
                [("url", "=like", f"{ESM_LIBS_URL_PREFIX}%")],
            ]
        )
        & Domain("url", "not like", f"{ESM_BRIDGES_URL_PREFIX}%"),
        ["url", "name"],
    )
    names_by_directory = defaultdict(list)
    for row in rows:
        names_by_directory[build_directory(row.url)].append(row.name)

    Build = env["ir.asset.build"]
    owned = Build._live_directories()
    now = fields.Datetime.now()
    vals_list = []
    for directory, names in sorted(names_by_directory.items()):
        if directory in owned:
            continue
        kind, bundle = _kind_and_bundle(directory, names)
        vals_list.append(
            {
                "kind": kind,
                "bundle": bundle,
                "variant": f"legacy:{directory}",
                "directories": [directory],
                "fingerprint": build_fingerprint([directory]),
                "state": "superseded",
                "superseded_at": now,
            }
        )
    Build.create(vals_list)
    _logger.info(
        "ESM asset builds: %d file(s) in %d directorie(s) adopted as superseded "
        "builds, %d by-source pointer(s) deleted",
        len(rows),
        len(vals_list),
        pointer_count,
    )
