import pathlib
import re

_FIELDS_DIR = pathlib.Path(__file__).resolve().parent.parent / "fields"

_CANONICAL = 'self.groups and not env.su and not {rec}._has_field_access(self, "read")'
_ALLOWED = {_CANONICAL.format(rec="record"), _CANONICAL.format(rec="records")}

_EXPECTED_SITES = {
    ("base.py", 1),
}


def _iter_sources():
    for path in sorted(_FIELDS_DIR.rglob("*.py")):
        rel = path.relative_to(_FIELDS_DIR).as_posix()
        flat = re.sub(r"\s+", " ", path.read_text())
        flat = re.sub(r"\(\s+", "(", flat)
        flat = re.sub(r"\s+\)", ")", flat)
        yield rel, flat


def _canonical_count(source: str) -> int:
    return sum(source.count(form) for form in _ALLOWED)


def test_every_field_access_check_uses_the_canonical_preamble():
    for rel, source in _iter_sources():
        total = source.count('_has_field_access(self, "read")')
        canonical = _canonical_count(source)
        assert total == canonical, (
            f"divergent field-ACL preamble in {rel}: {total} read-access check(s) "
            f"but only {canonical} in canonical form"
        )


def test_field_access_preamble_site_set_is_unchanged():
    counts: dict[str, int] = {}
    for rel, source in _iter_sources():
        if n := _canonical_count(source):
            counts[rel] = n
    assert set(counts.items()) == _EXPECTED_SITES, (
        f"field-ACL preamble sites changed: {sorted(counts.items())}. If this is "
        f"intentional, update _EXPECTED_SITES -- and make sure every copy still "
        f"matches the others."
    )


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
