"""Benchmark compute method performance using model_test_env.

Measures actual model code execution time (not ORM overhead) by running
compute methods in the in-memory test environment.

Usage::

    source ./venv/odoo/bin/activate
    PYTHONPATH=core python core/tests/bench_compute_methods.py
"""

import logging
import time

# Suppress ALL logging before any Odoo imports to prevent
# Field._update_cache() spam from overwhelming stdout.
logging.disable(logging.CRITICAL)

from odoo.orm.testing import ModelRegistry, model_test_env  # noqa: E402

from odoo.addons.base.models.res_partner import ResPartner  # noqa: E402


def bench(label: str, fn, n: int = 5000) -> tuple[str, float, int]:
    """Run fn() n times, return (label, microseconds_per_call, n)."""
    fn()  # warmup
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    elapsed = time.perf_counter() - t0
    us = elapsed / n * 1_000_000
    return (label, us, n)


def main():
    registry = ModelRegistry([ResPartner])
    results: list[tuple[str, float, int]] = []

    with model_test_env(registry=registry) as env:
        Partner = env["res.partner"]
        Country = env["res.country"]
        Currency = env["res.currency"]

        # --- Setup test data ---
        company = Partner.create(
            {"name": "ACME Corp", "is_company": True, "email": "info@acme.com"}
        )
        contact = Partner.create(
            {"name": "Alice Smith", "email": "alice@acme.com", "parent_id": company.id}
        )
        no_email = Partner.create({"name": "Bob", "is_company": False})
        batch3 = company | contact | no_email

        # Create larger batches for scaling analysis
        batch10 = Partner
        for i in range(10):
            batch10 |= Partner.create({"name": f"P{i}", "email": f"p{i}@x.com"})

        batch100 = Partner
        for i in range(100):
            batch100 |= Partner.create({"name": f"Q{i}", "email": f"q{i}@x.com"})

        mx = Country.create({"name": "Mexico", "code": "MX"})
        usd = Currency.create(
            {"name": "USD", "symbol": "$", "rounding": 0.01, "rate": 1.0}
        )

        # --- Compute Method Benchmarks ---
        print("=" * 75)
        print("COMPUTE METHOD BENCHMARKS")
        print("=" * 75)
        print()

        # res.partner computes
        results.append(
            bench(
                "_compute_display_name (single)",
                contact._compute_display_name,
            )
        )
        results.append(
            bench(
                "_compute_display_name (batch=3)",
                batch3._compute_display_name,
            )
        )
        results.append(
            bench(
                "_compute_display_name (batch=10)",
                batch10._compute_display_name,
            )
        )
        results.append(
            bench(
                "_compute_display_name (batch=100)",
                batch100._compute_display_name,
                n=1000,
            )
        )

        results.append(
            bench(
                "_compute_company_type (single)",
                company._compute_company_type,
            )
        )
        results.append(
            bench(
                "_compute_company_type (batch=3)",
                batch3._compute_company_type,
            )
        )

        results.append(
            bench(
                "_compute_email_formatted (single)",
                contact._compute_email_formatted,
            )
        )
        results.append(
            bench(
                "_compute_email_formatted (no email)",
                no_email._compute_email_formatted,
            )
        )
        results.append(
            bench(
                "_compute_email_formatted (batch=100)",
                batch100._compute_email_formatted,
                n=1000,
            )
        )

        results.append(
            bench(
                "_compute_complete_name (child with parent)",
                contact._compute_complete_name,
            )
        )
        results.append(
            bench(
                "_compute_complete_name (root company)",
                company._compute_complete_name,
            )
        )

        results.append(
            bench(
                "_compute_commercial_partner (child)",
                contact._compute_commercial_partner,
            )
        )
        results.append(
            bench(
                "_compute_commercial_partner (company)",
                company._compute_commercial_partner,
            )
        )

        results.append(
            bench(
                "_compute_commercial_company_name (child)",
                contact._compute_commercial_company_name,
            )
        )

        results.append(
            bench(
                "_compute_tz_offset (single)",
                contact._compute_tz_offset,
            )
        )

        results.append(
            bench(
                "_compute_type_address_label (contact)",
                contact._compute_type_address_label,
            )
        )

        # res.currency computes
        results.append(
            bench(
                "_compute_decimal_places (rounding=0.01)",
                usd._compute_decimal_places,
            )
        )

        # res.country computes
        results.append(
            bench(
                "_compute_image_url (country MX)",
                mx._compute_image_url,
            )
        )

        # --- Print compute results ---
        for label, us, n in results:
            print(f"  {label:55s} {us:8.1f} µs/call  ({n} iters)")

        # --- CRUD Benchmarks ---
        print()
        print("=" * 75)
        print("CRUD BENCHMARKS")
        print("=" * 75)
        print()

        crud_results = []

        # create()
        t0 = time.perf_counter()
        n_create = 2000
        for i in range(n_create):
            Partner.create({"name": f"Create{i}"})
        t1 = time.perf_counter()
        crud_results.append(("create() single record", (t1 - t0) / n_create * 1e6, n_create))

        # write()
        crud_results.append(
            bench("write() single field", lambda: contact.write({"name": "Alice Smith"}))
        )

        # read (field access)
        crud_results.append(
            bench("field read (contact.name)", lambda: contact.name)
        )

        # unlink()
        unlink_targets = [Partner.create({"name": f"Del{i}"}) for i in range(1000)]
        t0 = time.perf_counter()
        for target in unlink_targets:
            target.unlink()
        t1 = time.perf_counter()
        crud_results.append(("unlink() single record", (t1 - t0) / 1000 * 1e6, 1000))

        for label, us, n in crud_results:
            print(f"  {label:55s} {us:8.1f} µs/call  ({n} iters)")

        # --- Search Benchmarks ---
        print()
        print("=" * 75)
        print("SEARCH BENCHMARKS")
        print("=" * 75)
        print()

        total_records = len(Partner.search([]))
        print(f"  Total records in DictBackend: {total_records}")
        print()

        search_results = []
        search_results.extend((bench("search(name = 'Alice Smith')", lambda: Partner.search([("name", "=", "Alice Smith")]), n=1000), bench("search(is_company = True)", lambda: Partner.search([("is_company", "=", True)]), n=1000), bench("search(name ilike 'alice')", lambda: Partner.search([("name", "ilike", "alice")]), n=1000), bench("search(name in [list of 3])", lambda: Partner.search([("name", "in", ["Alice Smith", "Bob", "ACME Corp"])]), n=1000), bench("search([] - all records)", lambda: Partner.search([]), n=500)))

        for label, us, n in search_results:
            print(f"  {label:55s} {us:8.1f} µs/call  ({n} iters)")

        # --- Scaling Analysis ---
        print()
        print("=" * 75)
        print("SCALING: _compute_display_name vs batch size")
        print("=" * 75)
        print()

        for size in [1, 3, 10, 100]:
            if size == 1:
                rs = contact
            elif size == 3:
                rs = batch3
            elif size == 10:
                rs = batch10
            else:
                rs = batch100
            _, us, n = bench(f"batch={size}", lambda rs=rs: rs._compute_display_name(), n=2000)
            per_record = us / size
            print(f"  batch={size:>3d}: {us:8.1f} µs total, {per_record:8.1f} µs/record")


if __name__ == "__main__":
    main()
