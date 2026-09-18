import pathlib
import re

import pytest

from odoo.orm.runtime._registry_signaling import (
    CACHES_BY_KEY,
    REGISTRY_CACHES,
    SIGNALING_TABLES,
)

BUCKET_OWNERS: dict[str, str] = {
    "default": "the implicit bucket — ormcache's fallback when none is named",
    "assets": "base/web — compiled asset bundles",
    "assets.links": "base/web — the asset link map",
    "assets.files": (
        "base — ir.asset's per-pattern static-file globs. Its own bucket for "
        "the reason templates.mail has one: one page resolves 500-odd patterns, "
        "and in the 512-entry `assets` LRU they evicted the compiled bundle "
        "nodes, so a signed-in website page recompiled with esbuild on every "
        "request (measured, signed-in /contactus warm: 112 -> 18 queries)"
    ),
    "stable": "base — long-lived lookups (xmlids, ACLs, record-rule domains)",
    "templates": "base — QWeb template lookup",
    "templates.mail": (
        "the `mail` addon — mixin.mail.render._get_qweb_template_node, which "
        "parses a mail body and holds the programs compiled from it. Its own "
        "bucket because it is the one template cache keyed on arbitrary *text* "
        "rather than on a view reference: a composer body is a key that will "
        "never be seen again, so the population is unbounded and mostly "
        "one-shot, where every other member of `templates` is a bounded set of "
        "views. Sharing one LRU, 1000 unique mail bodies filled it and evicted "
        "every compiled view in the registry (measured, 5 -> 0)"
    ),
    "templates.cached_values": "base — values cached against a template render",
    "routing": "base/web — the HTTP routing map",
    "routing.rewrites": "base/web — URL rewrite rules",
    "groups": "base — group membership",
    "product_variants": (
        "the `product` addon — product.template._get_variant_id_for_combination "
        "and _get_first_possible_variant_id. Its own bucket because product "
        "churn invalidates it constantly, and a bare clear_cache() would "
        "otherwise evict `default` (record rules, ACLs, xmlids) in every worker "
        "each time a product is touched"
    ),
    "actions": (
        "base — ir.actions.actions._get_bindings, the sidebar bindings per "
        "model. Its own bucket because a binding change is signalled to every "
        "worker, and from `default` that signal evicted record rules, ACLs, "
        "menus and every other unnamed ormcache cluster-wide"
    ),
    "xmlid": (
        "base — ir.model.data._xmlid_target, hits and misses. Its own bucket "
        "because a miss is cached too (an optional xmlid probed on every request "
        "re-ran its SELECT forever when only hits were kept), so a fresh insert "
        "has to invalidate it, and from `default` that would have evicted record "
        "rules, ACLs and menus in every worker on each new xmlid"
    ),
    "mail": (
        "the `mail` addon — its small configuration snapshots: "
        "mail.message.subtype._get_auto_subscription_subtypes and _get_subtypes, "
        "and mail.alias._get_alias_addresses, the set every inbound email's "
        "recipients and authors are matched against. One bucket for the three "
        "because every check_signaling SELECT costs one scalar subquery per bucket, "
        "and each is one query to rebuild. Its own bucket because a subtype or "
        "alias create/write/unlink cleared `default` cluster-wide (5,687 misses of "
        "the first ormcache in a single suite, and an alias is created with every "
        "project, team or job); a bare clear_cache() still empties it, because "
        "`default` and `stable` list it"
    ),
}


def _repo_root() -> pathlib.Path:
    for parent in pathlib.Path(__file__).resolve().parents:
        if (parent / "odoo-bin").is_file():
            return parent
    raise RuntimeError("no odoo-bin marker above this test; cannot locate the checkout")


_CHECKOUT = _repo_root()
_SCAN_ROOTS = (_CHECKOUT / "odoo", _CHECKOUT / "addons")


def _consumer_counts() -> dict[str, int]:
    patterns = {
        b: re.compile(rf'(?:cache=|clear_cache\(\s*)["\']{re.escape(b)}["\']')
        for b in REGISTRY_CACHES
    }
    counts = dict.fromkeys(REGISTRY_CACHES, 0)
    here = pathlib.Path(__file__).resolve()
    for root in _SCAN_ROOTS:
        for path in root.rglob("*.py"):
            if path.name == "registry.py" or path.resolve() == here:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for bucket, pattern in patterns.items():
                counts[bucket] += len(pattern.findall(text))
    return counts


def test_the_bucket_set_is_closed():
    assert set(REGISTRY_CACHES) == set(BUCKET_OWNERS), (
        "REGISTRY_CACHES changed. Every bucket costs an orm_signaling_<name> "
        "table in every database, and most bucket names are addon vocabulary "
        "the import gates cannot see — so the set is pinned. Add the name to "
        "BUCKET_OWNERS with the consumer that justifies it."
    )


def test_every_bucket_has_a_consumer():
    counts = _consumer_counts()
    dead = sorted(b for b, n in counts.items() if n == 0 and b != "default")
    assert not dead, (
        f"cache bucket(s) with no consumer in this checkout: {dead}. Each is an "
        f"LRU allocated per registry and a table created in every database, for "
        f"nothing. Either something stopped using it, or it is used only from a "
        f"sibling repo — see _consumer_counts' docstring."
    )


def test_groups_only_name_real_buckets():
    for key, members in CACHES_BY_KEY.items():
        assert key in REGISTRY_CACHES, f"CACHES_BY_KEY key {key!r} is not a bucket"
        unknown = sorted(set(members) - set(REGISTRY_CACHES))
        assert not unknown, (
            f"group {key!r} names non-existent bucket(s) {unknown}. "
            f"_RegistryCaches.clear_group would raise KeyError on this group."
        )


def test_every_group_clears_itself():
    for key, members in CACHES_BY_KEY.items():
        assert key in members, (
            f"group {key!r} does not include {key!r}, so clear_cache({key!r}) "
            f"would clear its siblings and leave the named bucket warm"
        )


def test_signaling_tables_derive_from_the_groups():
    expected = tuple(f"orm_signaling_{name}" for name in ["registry", *CACHES_BY_KEY])
    assert expected == SIGNALING_TABLES
    assert len(set(SIGNALING_TABLES)) == len(SIGNALING_TABLES), "duplicate table"


def test_bucket_sizes_are_positive():
    bad = sorted(
        b
        for b, size in REGISTRY_CACHES.items()
        if not isinstance(size, int) or size <= 0
    )
    assert not bad, f"bucket(s) with a non-positive LRU size: {bad}"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
