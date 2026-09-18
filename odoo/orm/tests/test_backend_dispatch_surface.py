import ast
import pathlib
import re

import pytest

from odoo.orm.runtime._backend_memory import InMemoryBackend

_ORM_DIR = pathlib.Path(__file__).resolve().parent.parent

# Every place the ORM chooses between the SQL path and env.backend. The surface
# has grown to thirty sites across twenty files
# -- including seven in Layer 1, where a field reaches the backend directly
# rather than through a model mixin. Each entry says what the in-memory branch
# does NOT do, so a site marked LOSSY is a known gap, not an oversight.
# test_the_header_count_matches_the_dict parses these lines: the words are asserted.
DISPATCH_SITES: dict[tuple[str, str], str] = {
    ("models/mixins/create.py", "_create"): (
        "in-memory path skips the COPY fast path (performance only)"
    ),
    ("models/mixins/create.py", "_update_parent_path_on_create"): "equivalent",
    ("models/mixins/read.py", "_fetch_query"): (
        "equivalent: both fetches answer an inline binary's pg_size_pretty "
        "text under bin_size / bin_size_<field> and clear a stale PENDING "
        "marker of a stored compute before the row's value takes the cache"
    ),
    ("models/mixins/write.py", "_execute_update"): (
        "equivalent: PostgresBackend.update_rows merges jsonb translations "
        "(COALESCE(...jsonb_build_object('en_US', ...)) || expr) and "
        "company_dependent objects in SQL; InMemoryBackend.update_rows merges "
        "the same object over the stored row's dict, seeding en_US from the "
        "first value when the column was not an object yet"
    ),
    ("models/mixins/write.py", "_get_records_with_parent_changed"): "equivalent",
    ("models/mixins/write.py", "_increment_fields_skiplock"): (
        "equivalent: the rows that exist are incremented and counted; SKIP "
        "LOCKED has nothing to skip in memory, where no other transaction holds "
        "a row"
    ),
    ("models/mixins/schema.py", "_has_rows_in_table"): (
        "equivalent: has_rows_beyond(model, 0) on both tiers -- LIMIT 1 on "
        "PostgreSQL, the row count in memory"
    ),
    ("models/transient.py", "_remove_transient_rows_over_count"): (
        "equivalent: OFFSET n LIMIT 1 on PostgreSQL, the table's row count in "
        "memory, the same verdict on whether the vacuum has a backlog"
    ),
    ("models/mixins/write.py", "_update_parent_path_on_write"): "equivalent",
    ("models/mixins/unlink.py", "_unlink_process_batch"): (
        "equivalent: both unlink_rows refuse a record a company-dependent "
        "many2one with ondelete=restrict still names from a row that survives "
        "the batch (PostgreSQL scans after its DELETE, memory skips the rows "
        "its foreign-key plan deletes), clear the other "
        "company-dependent references and tell their dependents, and ask "
        "registry.metaschema about ir.default (the in-memory ir.default stub "
        "answers nothing); the foreign keys cascade, null or refuse through "
        "the database on PostgreSQL and through _ForeignKeyPlan in memory. The "
        "ir.model.data and ir.attachment rows left the port: the unlink mixin "
        "asks registry.xmlids and registry.file_store for them."
    ),
    ("models/mixins/search.py", "lock_for_update"): "equivalent",
    ("models/mixins/search.py", "try_lock_for_update"): "equivalent",
    ("models/mixins/_query.py", "_search"): "equivalent",
    ("models/mixins/_query.py", "_as_query"): "equivalent",
    ("models/mixins/_query.py", "exists"): "equivalent",
    ("models/mixins/_properties.py", "get_property_definition"): (
        "equivalent: the definition column is scanned as stored through "
        "backend.columns.get_column_values -- every row holding one, by id -- and the first "
        "entry naming the property answers, the raw jsonb on PostgreSQL and the "
        "row's dict in memory, an invalid comodel written to it included"
    ),
    ("fields/temporal.py", "_resolve_sql_timezone_name"): (
        "equivalent: the zone names timezone() accepts, read once per database "
        "from pg_timezone_names on PostgreSQL and from zoneinfo in memory, which "
        "is what the in-memory read_group converts with"
    ),
    ("models/mixins/read_group/sql.py", "_read_group_groupby_temporal"): (
        "equivalent: the same timezone_names lookup for a datetime property"
    ),
    ("fields/reference.py", "_reference_exists"): (
        "equivalent: the siblings' stored pairs are read through "
        "backend.columns on both tiers and verified in the same round, where "
        "a raw SELECT DISTINCT ran on PostgreSQL alone"
    ),
    ("fields/relational/many2many.py", "read"): "equivalent",
    ("fields/count.py", "_count_in_database"): (
        "equivalent: a Count on a many2many asks count_m2m_groups for one row "
        "per record (count(*) GROUP BY on PostgreSQL, the pairs' length in "
        "memory) after flushing the counted relation"
    ),
    ("fields/relational/many2many.py", "_apply_relation_delta"): "equivalent",
    ("fields/_field_translation.py", "get_stored_translations"): (
        "equivalent: both branches read the stored column through "
        "backend.columns; the in-memory store may hold a plain string, which "
        "is wrapped as {'en_US': value}"
    ),
    ("models/mixins/translation.py", "_update_model_translations"): (
        "the jsonb merge of update_field_translations runs through "
        "backend.columns.merge_json: fallback under stored under value, null "
        "entries stripped, an empty object stored as NULL -- the in-memory "
        "store merges the same three layers on the row's dict"
    ),
    ("fields/_field_translation.py", "get_stored_translations_multi"): (
        "equivalent: one read of the stored column for every record through "
        "backend.columns, same wrapping as the single-record read"
    ),
    ("models/mixins/read_group/mixin.py", "_read_group"): (
        "LOSSY: PostgresBackend runs the compiled statement; InMemoryBackend "
        "groups the dict rows itself and covers column, many2one, many2one "
        "path, many2many and property groupbys (tags and many2many properties "
        "one key per known element), every granularity, the standard "
        "aggregates (exact on numeric columns; sum_currency through the rates "
        "the Locale port picks as the SQL subquery does), having, an explicit "
        "order (an aggregate term outside the selection is computed for the "
        "sort alone, as the SQL path selects it; an array aggregate sorts as "
        "PostgreSQL compares arrays, element by element with a NULL element "
        "last), limit and offset; the "
        "empty-having probe of a query matching nothing goes through the same "
        "method, PostgreSQL counting over WHERE FALSE and memory aggregating "
        "over no record, the having clause deciding on both"
    ),
    ("models/mixins/read_group/mixin.py", "_read_grouping_sets"): (
        "equivalent: PostgresBackend runs the GROUPING SETS statement; "
        "InMemoryBackend groups once per set through the in-memory read_group, "
        "each set sorted by the order terms it carries, and shapes the rows as "
        "SQL does -- the GROUPING() mask, every groupby column (NULL when the "
        "set lacks it), the aggregates -- so the mixin dispatches them unchanged"
    ),
    ("models/mixins/traversal.py", "_has_cycle"): (
        "equivalent: the reachability CTE over the relation on PostgreSQL, the "
        "same closure walked over the relation rows in memory, the same verdict; "
        "the mixin only names the relation (the table and its many2one column, "
        "or the many2many triple) and flushes it first"
    ),
    ("runtime/recordset_cache.py", "process"): (
        "equivalent: Cache.check reads a stored column through backend.columns "
        "on both tiers (the SQL path stays for a model with a _table_query), so "
        "the DB-free harness asserts cache-against-rows after every test as "
        "TransactionCase does against PostgreSQL"
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


def test_in_memory_unlink_rows_only_removes_rows():
    import inspect

    params = list(inspect.signature(InMemoryBackend.unlink_rows).parameters)
    assert params == ["self", "model", "sub_ids"], (
        "unlink_rows grew an argument. The meta-schema, xmlid and file ports "
        "took the base models out of its signature; a new one belongs on a port, "
        "not on the storage backend."
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
        "_order_value_to_sql",
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
    "twenty-one": 21,
    "twenty-two": 22,
    "twenty-three": 23,
    "twenty-four": 24,
    "twenty-five": 25,
    "twenty-six": 26,
    "twenty-seven": 27,
    "twenty-eight": 28,
    "twenty-nine": 29,
    "thirty": 30,
}


def test_the_header_count_matches_the_dict():
    header = (
        pathlib.Path(__file__)
        .read_text(encoding="utf-8")
        .split("DISPATCH_SITES: dict", 1)[0]
    )
    stated = re.search(
        r"grown to ([\w-]+) sites across (\w+) files\s*"
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
