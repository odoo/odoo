import logging
from pathlib import Path

from odoo.libs.lint.scan import scan_byte_patterns

from . import lint_case

_logger = logging.getLogger(__name__)

MARKERS = [b"<" * 7, b">" * 7]
EXTENSIONS = [".py", ".js", ".xml", ".less", ".sass"]


class TestConflictMarkers(lint_case.LintCase):

    def test_conflict_markers(self):
        """Test that there are no conflict markers left in Odoo files."""
        import odoo.addons

        roots = sorted(
            {str(Path(p).resolve()) for p in [*odoo.addons.__path__, *odoo.__path__]}
        )

        results = scan_byte_patterns(
            roots,
            EXTENSIONS,
            MARKERS,
            ["node_modules", "__pycache__"],
        )

        if results:
            results.sort()
            msg = "Conflict markers found:\n" + "\n".join(
                f"- {path}:{line}" for path, line, _ in results
            )
            self.fail(msg)

        _logger.info("conflict marker scan complete (no violations)")
