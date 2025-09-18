"""Parallel file scanning for lint tests.

Tries to import the Rust-accelerated ``odoo_rust.scan_byte_patterns`` and
``odoo_rust.scan_regex_patterns``.  Falls back to a sequential pure-Python
implementation if the extension is not available.
"""

import re
from pathlib import Path

try:
    from odoo_rust import scan_byte_patterns, scan_regex_patterns
except ImportError:

    def scan_byte_patterns(
        roots: list[str],
        extensions: list[str],
        patterns: list[bytes],
        exclude_dirs: list[str],
    ) -> list[tuple[str, int, int]]:
        """Sequential fallback for byte-pattern scanning."""
        ext_set = {e if e.startswith(".") else f".{e}" for e in extensions}
        exclude = set(exclude_dirs)
        results: list[tuple[str, int, int]] = []

        for root in roots:
            for dirpath, dirnames, filenames in Path(root).walk():
                dirnames[:] = [d for d in dirnames if d not in exclude]
                for fn in filenames:
                    if not any(fn.endswith(ext) for ext in ext_set):
                        continue
                    path = str(dirpath / fn)
                    try:
                        content = Path(path).read_bytes()
                    except OSError:
                        continue
                    for idx, pat in enumerate(patterns):
                        start = 0
                        while (pos := content.find(pat, start)) != -1:
                            line = content[:pos].count(b"\n") + 1
                            results.append((path, line, idx))
                            start = pos + 1
        return results

    def scan_regex_patterns(
        roots: list[str],
        extensions: list[str],
        patterns: list[str],
        exclude_dirs: list[str],
    ) -> list[tuple[str, int, int, str]]:
        """Sequential fallback for regex-pattern scanning."""
        ext_set = {e if e.startswith(".") else f".{e}" for e in extensions}
        exclude = set(exclude_dirs)
        compiled = [re.compile(p, re.DOTALL) for p in patterns]
        results: list[tuple[str, int, int, str]] = []

        for root in roots:
            for dirpath, dirnames, filenames in Path(root).walk():
                dirnames[:] = [d for d in dirnames if d not in exclude]
                for fn in filenames:
                    if not any(fn.endswith(ext) for ext in ext_set):
                        continue
                    path = str(dirpath / fn)
                    try:
                        text = Path(path).read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    for idx, rx in enumerate(compiled):
                        for m in rx.finditer(text):
                            line = text[: m.start()].count("\n") + 1
                            results.append((path, line, idx, m.group(0)))
        return results
