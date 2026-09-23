{
    "name": "Test Performance Compare",
    "version": "1.0",
    "category": "Hidden/Tests",
    "summary": "Portable cross-version ORM benchmark (fork vs upstream 19.0).",
    "description": """
Portable ORM benchmark for A/B comparison between this fork and a vanilla
Odoo 19.0 checkout.

Unlike ``test_performance`` (which is fork-only and couples to refactored
internals such as ``odoo.tests.benchmark``, ``FieldCache``, specialised field
``__get__``, ``fast_clone`` …), this module is **fully self-contained**:

* depends only on ``base``;
* defines its own models (no shared data, deterministic state);
* vendors its own timing + query-count harness (``tests/perfkit.py``) that
  relies solely on public, version-stable APIs (``cr.sql_log_count`` and
  ``time.perf_counter_ns``);
* imports nothing fork-specific, so the whole folder can be dropped, unchanged,
  into a vanilla 19.0 addons path and produces a comparable result file.

See ``README.md`` for the full A/B runbook.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/ir.access.csv",
    ],
}
