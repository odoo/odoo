"""Two ratchets on the ORM's shape after the persistence and port moves of
2026-09-13 (agromarin-knowledge/research/2026-09-13-concern-and-modularity-map.md).

Each pin is a frozen map of file -> count that may shrink and must not grow: a
regression names the file; a move that removes a site lowers the pin in the
same change."""

import pathlib
import re

_ORM_DIR = pathlib.Path(__file__).resolve().parent.parent

# the six objects through which the ORM talks to addons/base
_PORT_FILES = {
    "runtime/metaschema.py",
    "runtime/access_policy.py",
    "runtime/xmlids.py",
    "runtime/filestore.py",
    "runtime/settings.py",
    "runtime/locale.py",
}

# `env["<base model>"]` outside the ports: the singletons the map left, by file
BASE_MODEL_REACHES = {
    "fields/properties.py": 2,  # env["base"], the properties-definition hooks
    "helpers.py": 1,  # res.company, the company check
    "models/mixins/access.py": 1,  # res.groups, the company-crossover message
    "models/mixins/load.py": 1,  # ir.fields.converter
    "models/mixins/read_group/sql.py": 1,  # res.currency.rate, sum_currency
    "model_test_env.py": 2,  # ir.model, ir.model.fields: the in-memory reflection
}

# statements the models, fields and domain layers still execute themselves;
# everything else goes through env.backend and its ports
EXECUTED_STATEMENTS = {
    "models/mixins/schema.py": 2,
    "fields/_field_ddl.py": 3,
}

# either quote: the one site that spelled env['ir.model'] inside an f-string
# escaped the double-quoted form of this pattern until 2026-09-15
_REACH = re.compile(r"""env\[["'](?:ir|res|base|decimal)[a-z._]*["']\]""")
_EXECUTE = re.compile(r"\bcr\.execute\(|\bexecute_query\(")


def _count(pattern: re.Pattern, roots: tuple[str, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for root in roots:
        base = _ORM_DIR / root if root else _ORM_DIR
        files = base.rglob("*.py") if base.is_dir() else [base]
        for path in files:
            rel = path.relative_to(_ORM_DIR).as_posix()
            if "/tests/" in f"/{rel}" or rel in _PORT_FILES:
                continue
            n = len(pattern.findall(path.read_text()))
            if n:
                counts[rel] = n
    return counts


def _ratchet(found: dict[str, int], pinned: dict[str, int], what: str) -> None:
    grown = {f: n for f, n in found.items() if n > pinned.get(f, 0)}
    assert not grown, (
        f"{what} grew: {grown}. The ORM reaches storage and base through "
        f"env.backend and the port objects; a new site belongs on one of them."
    )
    shrunk = {f: pinned[f] for f in pinned if found.get(f, 0) < pinned[f]}
    assert not shrunk, (
        f"{what} shrank: {shrunk}. Good news, but pin it: lower these counts in "
        f"odoo/orm/tests/test_architecture_pins.py so the shrink cannot be undone."
    )


def test_the_orm_names_base_models_only_through_the_ports_plus_the_pinned_few():
    found = _count(_REACH, ("",))
    _ratchet(found, BASE_MODEL_REACHES, "env['<base model>'] reaches outside the ports")


def test_the_models_fields_and_domain_layers_execute_only_the_pinned_statements():
    found = _count(_EXECUTE, ("models", "fields", "domain"))
    _ratchet(found, EXECUTED_STATEMENTS, "statements executed outside env.backend")
