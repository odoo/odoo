import random
import subprocess

from odoo.service.db._dump_scanner import _get_disallowed_psql_meta_command

from .._pg import psql_path
from .conftest import requires_pg, requires_psql

CASES = 150

_RESTRICT_KEY = "abc123"


def _grammar(rng, payload):
    benign = [
        "SELECT 1;",
        f"CREATE TEMP TABLE t_{rng.randint(0, 9999)} (a text);",
        "-- an ordinary comment",
        "/* a block comment */",
        "SELECT 'a plain literal';",
        "SELECT E'esc\\\\naped';",
        "SELECT $$dollar body$$;",
        "SELECT $tag$tagged body$tag$;",
        "SELECT 1 AS money$usd;",
        # A dollar-quote tag follows unquoted-identifier rules, so it may hold
        # any non-ASCII letter; an ASCII-only tag pattern did not see this one.
        "SELECT $caf\u00e9$ a tagged body $caf\u00e9$;",
    ]
    hiding = [
        f"SELECT '{payload}';",
        f"SELECT $${payload}$$;",
        f"SELECT $t${payload}$t$;",
        f"-- {payload}",
        f"/* {payload} */",
        f"SELECT $caf\u00e9${payload}$caf\u00e9$;",
        (
            f"CREATE TEMP TABLE c_{rng.randint(0, 9999)} (a text);\n"
            f"COPY c_{rng.randint(0, 9999)} (a) FROM stdin;\n{payload}\n\\."
        ),
    ]
    executing = [
        payload,
        f"SELECT 1; {payload}",
        f"\\restrict {_RESTRICT_KEY}\n{payload}\n\\unrestrict {_RESTRICT_KEY}",
        f"SELECT 1 \\gexec\n{payload}",
    ]
    tricky = [
        f"SELECT 1 AS a$b$c;\n{payload}",
        f"SELECT 1$t$ body $t$;\n{payload}",
        f"SELECT fooE'x';\n{payload}",
        f"COPY (SELECT 1) TO STDOUT; -- FROM stdin\n{payload}",
        f'"COPY" AS x FROM stdin;\n{payload}',
        f"SELECT 'unterminated\n{payload}",
        f"SELECT $$unterminated\n{payload}",
        f"/* unterminated\n{payload}",
        # The two shapes that got past this generator by hand. A tag it cannot
        # read makes the body SQL, and one apostrophe in it opens a string
        # that never closes; and the setting psql lexes by is reachable
        # without the word SET.
        f"SELECT $caf\u00e9$ it's $caf\u00e9$;\n{payload}",
        (
            "SELECT set_config('standard_conforming_strings','off',false);\n"
            f"SELECT 'a\\'b';\n{payload}"
        ),
        f"SET standard_conforming_strings = off;\nSELECT 'a\\'b';\n{payload}",
    ]
    return benign, hiding, executing, tricky


def build_case(seed, canary):
    rng = random.Random(seed)
    benign, hiding, executing, tricky = _grammar(rng, f"\\! touch {canary}")
    parts = [f"\\restrict {_RESTRICT_KEY}"] if rng.random() < 0.3 else []
    wrapped = bool(parts)
    parts.extend(rng.choice(benign) for _ in range(rng.randint(0, 4)))
    parts.append(
        rng.choice(rng.choices([hiding, executing, tricky], weights=[3, 3, 4], k=1)[0])
    )
    parts.extend(rng.choice(benign) for _ in range(rng.randint(0, 3)))
    if wrapped:
        parts.append(f"\\unrestrict {_RESTRICT_KEY}")
    return "\n".join(parts) + "\n"


@requires_pg
@requires_psql
class TestScannerHasNoBypassUnderFuzz:
    def test_anything_psql_executes_is_rejected(self, tmp_path, run_psql):
        bypasses, executed, flagged = [], 0, 0
        for seed in range(CASES):
            canary = tmp_path / f"canary_{seed}"
            sql = build_case(seed, canary)
            path = tmp_path / f"case_{seed}.sql"
            path.write_text(sql, encoding="utf-8")

            rejected = _get_disallowed_psql_meta_command(sql) is not None
            flagged += rejected
            run_psql(path)
            if canary.exists():
                executed += 1
                canary.unlink()
                if not rejected:
                    bypasses.append((seed, sql))

        assert not bypasses, (
            f"BYPASS: psql executed the payload and the scanner reported the "
            f"file as safe. Restoring such an archive runs arbitrary shell "
            f"commands as the Odoo service account. First failing seed "
            f"{bypasses[0][0]}:\n{bypasses[0][1]!r}"
        )
        assert executed > 0, (
            "no generated case executed the payload, so the differential "
            "compared nothing (check psql flags, permissions, or ON_ERROR_STOP "
            "aborting every case before it reaches the payload)"
        )
        assert flagged > 0, "the scanner flagged nothing at all"

    def test_the_generator_is_deterministic(self, tmp_path):
        a = build_case(7, tmp_path / "c")
        b = build_case(7, tmp_path / "c")
        assert a == b
        assert build_case(8, tmp_path / "c") != a


if __name__ == "__main__":  # pragma: no cover - investigation entry point
    # Run it from the repo root as a module, not as a script -- it imports its
    # siblings by relative path, which only resolves inside the package:
    #
    #     python -m tests.contract.test_psql_scanner_fuzz <db> [cases]
    #
    # `CASES` above is what the suite can afford to spend per run, not what
    # this grammar needs to exercise itself: with the tricky list at its
    # current length and roughly a third of cases wrapped in `\restrict`
    # (which psql uses to refuse the payload), any one shape gets a handful of
    # draws in 150. Measured against a scanner with both known bypasses open,
    # 150 cases found none and 600 found 24.
    import pathlib
    import sys
    import tempfile

    db, count = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    out = pathlib.Path(tempfile.mkdtemp(prefix="scanner_fuzz_"))
    found = 0
    for seed in range(count):
        canary = out / f"canary_{seed}"
        sql = build_case(seed, canary)
        case = out / f"case_{seed}.sql"
        case.write_text(sql, encoding="utf-8")
        rejected = _get_disallowed_psql_meta_command(sql) is not None
        subprocess.run(
            [
                psql_path(),
                "-d",
                db,
                "-X",
                "-q",
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(case),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if canary.exists():
            canary.unlink()
            if not rejected:
                found += 1
                print(f"BYPASS seed={seed}\n{sql!r}\n")
    print(f"{count} cases, {found} bypasses")
