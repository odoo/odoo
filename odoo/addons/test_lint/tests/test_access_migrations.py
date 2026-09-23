import io
import re
import tempfile
import tokenize
from pathlib import Path

from . import lint_case

_RETIRED_ACCESS_NAMES = re.compile(
    r"\bir_rule\b|\bir_model_access\b|\brule_group_rel\b"
    r"|\bir\.rule\b|\bir\.model\.access\b"
)


def _is_migration(path) -> bool:
    parts = Path(path).parts
    return path.endswith(".py") and ("migrations" in parts or "upgrades" in parts)


def _reads_the_old_tables_by_design(path) -> bool:
    # base converts the two tables in 1.97's pre stage and drops them in 1.100;
    # only its pre-migrates older than 1.97 ran while they were the live data
    parts = Path(path).parts
    if len(parts) < 4 or parts[-4:-2] != ("base", "migrations"):
        return False
    version = tuple(int(n) for n in parts[-2].split(".") if n.isdigit())
    return version in ((1, 97), (1, 100)) or (
        version < (1, 97) and parts[-1].startswith("pre-")
    )


def migration_findings(paths):
    # every other module migrates after base 1.97 has converted both tables, so
    # a script still aimed at them edits rows nothing reads any more
    findings = []
    for path in paths:
        if not _is_migration(path) or _reads_the_old_tables_by_design(path):
            continue
        try:
            source = Path(path).read_text(encoding="utf-8")
            tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        except OSError, UnicodeDecodeError, SyntaxError, tokenize.TokenError:
            continue
        findings.extend(
            f"{path}:{token.start[0]} {match.group()}"
            for token in tokens
            if token.type != tokenize.COMMENT
            and (match := _RETIRED_ACCESS_NAMES.search(token.string))
        )
    return findings


class TestMigrationsReadIrAccess(lint_case.LintCase):
    def test_no_migration_reaches_for_the_retired_tables(self):
        self.assert_ratchet(
            migration_findings(lint_case.module_file_paths()),
            "access_migration_retired_tables",
            "migration script(s) reading or writing ir_rule or ir_model_access",
            "Base converts both tables before any other module migrates, so the "
            "script edits rows nothing reads: aim it at ir_access through "
            "ir_access_convert's converted_row_ids, rewrite_converted_domain, "
            "replace_in_converted_domains, delete_converted_rows or "
            "move_access_group.",
        )

    def test_a_migration_reaching_for_the_retired_tables(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        scripts = {
            "sale/migrations/1.2/post-migrate.py": (
                "def migrate(cr, version):\n"
                '    cr.execute("UPDATE ir_rule SET active = false")\n'
                "    env['ir.model.access'].search([])\n"
            ),
            "sale/migrations/1.3/post-migrate.py": (
                "def migrate(cr, version):\n"
                "    # the rule ir_rule_sale_x lived in ir_rule once\n"
                '    cr.execute("UPDATE ir_access SET active = false")\n'
                "    rewrite_converted_domain(cr, 'sale', 'ir_rule_sale_x', '[]')\n"
            ),
            "base/migrations/1.50/pre-migrate.py": "q = 'SELECT 1 FROM ir_rule'\n",
            "base/migrations/1.50/post-migrate.py": "q = 'SELECT 1 FROM ir_rule'\n",
            "base/migrations/1.97/pre-migrate.py": "q = 'SELECT 1 FROM ir_rule'\n",
            "base/migrations/1.98/pre-migrate.py": "q = 'SELECT 1 FROM ir_rule'\n",
            "sale/models/sale.py": "q = 'SELECT 1 FROM ir_rule'\n",
        }
        for name, text in scripts.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text)
        findings = migration_findings(str(root / name) for name in scripts)
        self.assertEqual(
            sorted(finding.split(str(root) + "/")[1] for finding in findings),
            [
                "base/migrations/1.50/post-migrate.py:1 ir_rule",
                "base/migrations/1.98/pre-migrate.py:1 ir_rule",
                "sale/migrations/1.2/post-migrate.py:2 ir_rule",
                "sale/migrations/1.2/post-migrate.py:3 ir.model.access",
            ],
        )
