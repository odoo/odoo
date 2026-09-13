import ast
import pathlib
import re

import pytest

from odoo.orm.runtime.backend import InMemoryBackend

_ORM_DIR = pathlib.Path(__file__).resolve().parent.parent

# Every place the ORM chooses between the SQL path and env.backend. The surface
# has grown to twenty sites across twelve files
# -- including six in Layer 1, where a field reaches the backend directly
# rather than through a model mixin. Each entry says what the in-memory branch
# does NOT do, so a site marked LOSSY is a known gap, not an oversight.
# test_the_header_count_matches_the_dict parses these lines: the words are asserted.
DISPATCH_SITES: dict[tuple[str, str], str] = {
    ("models/mixins/create.py", "_create"): (
        "in-memory path skips the COPY fast path (performance only)"
    ),
    ("models/mixins/create.py", "_update_parent_path_on_create"): (
        "guarded by backend.supports_parent_store"
    ),
    ("models/mixins/read.py", "_fetch_query"): (
        "LOSSY: PostgresBackend.fetch applies bin_size / bin_size_<field> "
        "(pg_size_pretty) and to_flush bookkeeping; InMemoryBackend.fetch "
        "does not"
    ),
    ("models/mixins/write.py", "_execute_update"): (
        "LOSSY: PostgresBackend.update_rows merges jsonb translations "
        "(COALESCE(...jsonb_build_object('en_US', ...)) || expr) and handles "
        "company_dependent columns; InMemoryBackend.update_rows does neither"
    ),
    ("models/mixins/write.py", "_get_records_with_parent_changed"): (
        "guarded by backend.supports_parent_store"
    ),
    ("models/mixins/unlink.py", "_unlink_process_batch"): (
        "LOSSY: PostgresBackend.unlink_rows runs the many2one_company_dependents "
        "ir.default cleanup; InMemoryBackend.unlink_rows() only removes the rows. "
        "It IS passed the Defaults recordset -- extracting PostgresBackend showed "
        "the port's signature was missing an argument the operation needs. The "
        "ir.model.data and ir.attachment rows left the port: the unlink mixin asks "
        "registry.xmlids and registry.file_store for them, so both tiers collect "
        "them alike."
    ),
    ("models/mixins/search.py", "lock_for_update"): "equivalent",
    ("models/mixins/search.py", "try_lock_for_update"): "equivalent",
    ("models/mixins/_query.py", "_search"): "equivalent",
    ("models/mixins/_query.py", "_as_query"): "equivalent",
    ("models/mixins/_query.py", "exists"): "equivalent",
    ("fields/reference.py", "_reference_exists"): (
        "BACKEND-SNIFF: `env.backend is None` gates a prefetch SELECT, i.e. it "
        "reads as 'am I on PostgreSQL?'.  This is the inline test-backend sniff "
        "the persistence port set out to remove, renamed from transaction.storage"
    ),
    ("fields/relational/many2many.py", "read"): "equivalent",
    ("fields/relational/many2many.py", "_apply_relation_delta"): "equivalent",
    ("fields/_field_translation.py", "get_mirrored_ids_by_language"): (
        "LOSSY: the SQL branch reads the stored jsonb translations and returns "
        "every other language whose term is an *echo* of `lang`'s, so a write "
        "in `lang` propagates to them.  The in-memory branch has no jsonb "
        "column to compare against and returns {} unconditionally, so on that "
        "backend no translation ever follows a write.  A DB-free test of "
        "translation propagation therefore cannot fail for the right reason"
    ),
    ("fields/_field_translation.py", "get_stored_translations"): (
        "equivalent: both branches read the stored column through "
        "backend.columns; the in-memory store may hold a plain string, which "
        "is wrapped as {'en_US': value}"
    ),
    ("fields/_field_translation.py", "get_stored_translations_multi"): (
        "equivalent: one read of the stored column for every record through "
        "backend.columns, same wrapping as the single-record read"
    ),
    ("models/mixins/read_group/mixin.py", "_read_group"): (
        "LOSSY: PostgresBackend runs the compiled statement; InMemoryBackend "
        "groups the dict rows itself and covers column and many2one groupbys, "
        "day/week/month/quarter/year granularity and the standard aggregates, "
        "and raises NotImplementedError for many2one paths, many2many and "
        "properties groupbys, having, an explicit order and sum_currency"
    ),
    ("models/mixins/traversal.py", "_has_cycle"): (
        "guarded by backend.supports_recursive_queries: the reachability CTE on "
        "PostgreSQL, one relation read per step in memory, the same verdict"
    ),
    ("domain/optimizations.py", "_get_domain_child_of"): (
        "equivalent: the transitive closure of a many2one on a model without "
        "parent_store -- one recursive CTE on PostgreSQL, one search per level "
        "in memory, the same id set either way"
    ),
}

LAYER1_PREFIXES = ("fields/",)


def _dispatch_sites() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in sorted(_ORM_DIR.rglob("*.py")):
        rel = path.relative_to(_ORM_DIR).as_posix()
        if "tests/" in rel or path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text())
        parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute) and node.attr == "backend"):
                continue
            owner = node.value
            is_env = (isinstance(owner, ast.Name) and owner.id == "env") or (
                isinstance(owner, ast.Attribute) and owner.attr == "env"
            )
            if not is_env:
                continue
            enclosing: ast.AST = node
            while enclosing in parents:
                enclosing = parents[enclosing]
                if isinstance(enclosing, ast.FunctionDef | ast.AsyncFunctionDef):
                    found.add((rel, enclosing.name))
                    break
    return found


def test_dispatch_surface_matches_the_pinned_inventory():
    found = _dispatch_sites()
    pinned = set(DISPATCH_SITES)
    added = sorted(found - pinned)
    removed = sorted(pinned - found)
    assert not added, (
        f"new env.backend dispatch site(s): {added}. Each one is a place the "
        f"in-memory and SQL persistence paths may diverge. Add it to "
        f"DISPATCH_SITES with a note stating whether the two branches are "
        f"behaviourally equivalent."
    )
    assert not removed, (
        f"env.backend dispatch site(s) gone: {removed}. Good news, but pin it: "
        f"remove the entry from DISPATCH_SITES so the shrink cannot be undone "
        f"silently."
    )


def test_layer1_dispatch_stays_explicitly_enumerated():
    layer1 = {site for site in _dispatch_sites() if site[0].startswith(LAYER1_PREFIXES)}
    pinned_layer1 = {
        site for site in DISPATCH_SITES if site[0].startswith(LAYER1_PREFIXES)
    }
    assert layer1 == pinned_layer1, (
        f"Layer-1 env.backend dispatch changed: {sorted(layer1 ^ pinned_layer1)}. "
        f"The persistence port is scoped to the model mixins; a new Layer-1 "
        f"dispatch widens its blast radius past that scope."
    )


def test_in_memory_unlink_rows_is_declared_lossy():
    import inspect

    params = list(inspect.signature(InMemoryBackend.unlink_rows).parameters)
    assert "Defaults" in params, (
        "InMemoryBackend.unlink_rows no longer receives Defaults. It gained the "
        "argument when PostgresBackend was extracted and the SQL path started "
        "going through the port, which showed the signature was missing "
        "something the operation needs. Narrowing the port back would re-open "
        "the wider half of this divergence."
    )


def test_lossy_sites_are_spelled_out():
    for site, note in DISPATCH_SITES.items():
        if note.startswith("LOSSY"):
            assert len(note) > 60, f"{site}: LOSSY note must say what is lost"


QUERY_COMPILERS = frozenset(
    {
        "_field_to_sql",
        "_order_to_sql",
        "_order_field_to_sql",
        "_traverse_related_sql",
        "_table_sql",
    }
)


def _mixin_sql_methods() -> set[str]:
    found: set[str] = set()
    for path in sorted((_ORM_DIR / "models" / "mixins").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.FunctionDef) and node.name.endswith("_sql"):
                found.add(node.name)
    return found


def test_the_mixins_hold_no_row_io_sql():
    row_io = sorted(_mixin_sql_methods() - QUERY_COMPILERS)
    assert not row_io, (
        f"row I/O SQL is back on the model mixins: {row_io}. It belongs on "
        f"PostgresBackend, so that env.backend is the whole persistence port "
        f"and not a dispatch table into the model; a query compiler goes in "
        f"QUERY_COMPILERS instead."
    )
    assert _mixin_sql_methods() >= QUERY_COMPILERS, (
        "QUERY_COMPILERS names a method the mixins no longer define"
    )


def test_postgres_backend_calls_only_query_compilers_on_the_model():
    import inspect

    from odoo.orm.runtime.backend import PostgresBackend

    called = set(re.findall(r"model\.(_\w+_sql)\(", inspect.getsource(PostgresBackend)))
    dispatched_back = sorted(called - QUERY_COMPILERS)
    assert not dispatched_back, (
        f"PostgresBackend dispatches back into the model for {dispatched_back}: "
        f"the SQL side of the port is a dispatch table again"
    )


_NUMBER_WORDS = {
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def test_the_header_count_matches_the_dict():
    header = (
        pathlib.Path(__file__)
        .read_text(encoding="utf-8")
        .split("DISPATCH_SITES: dict", 1)[0]
    )
    stated = re.search(
        r"grown to (\w+) sites across (\w+) files\s*"
        r"#\s*-- including (\w+) in Layer 1",
        header,
    )
    assert stated, "the header no longer states the surface size in the pinned shape"
    sites, files, layer1 = (_NUMBER_WORDS[w] for w in stated.groups())

    assert sites == len(DISPATCH_SITES)
    assert files == len({site[0] for site in DISPATCH_SITES})
    assert layer1 == len(
        [s for s in DISPATCH_SITES if s[0].startswith(LAYER1_PREFIXES)]
    )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
