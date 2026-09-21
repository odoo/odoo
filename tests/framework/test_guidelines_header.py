"""The guide's header against its own change log.

`doc/coding_guidelines.rst`'s *Change protocol* makes an Appendix D row
mandatory for every rule change, and the header's `:Version:` and `:Date:`
are what a reader -- or another document citing "§2.4 as of 6.57" -- takes
the guide's state from.  Nothing paired the two, so they drifted: measured
2026-09-21, the header read 6.58 / 2026-09-16 against a top row of 6.59 /
2026-09-20, one commit after the row landed without the bump.

A version that lags is worse than one that is absent, because it reads as a
statement.  Neither expected value is written here: both are read out of the
table, so the only way to pass is to move the header when the row moves.
"""

import pathlib
import re

import pytest

GUIDE = pathlib.Path(__file__).resolve().parents[2] / "doc" / "coding_guidelines.rst"

_ROW = re.compile(
    r"^   \* - (?P<version>\d+\.\d+)\n\s+- (?P<date>\d{4}-\d{2}-\d{2})\n", re.MULTILINE
)


@pytest.fixture(scope="module")
def guide() -> str:
    assert GUIDE.is_file(), f"the coding guide moved from {GUIDE}"
    return GUIDE.read_text()


@pytest.fixture(scope="module")
def newest_row(guide) -> re.Match:
    appendix = guide[guide.index("Appendix D — Document history") :]
    row = _ROW.search(appendix)
    assert row, "Appendix D no longer opens with a version/date row"
    return row


class TestTheHeaderStatesTheNewestChange:
    def test_the_version_is_appendix_d_s_newest_row(self, guide, newest_row):
        stated = re.search(r"^:Version: (\S+)$", guide, re.MULTILINE)
        assert stated, "the guide lost its :Version: header"
        assert stated[1] == newest_row["version"], (
            f":Version: says {stated[1]} and Appendix D's newest row is "
            f"{newest_row['version']}; a reader citing a section 'as of' a "
            f"version is citing the wrong one"
        )

    def test_the_date_is_that_row_s_date(self, guide, newest_row):
        stated = re.search(r"^:Date: (\S+)$", guide, re.MULTILINE)
        assert stated, "the guide lost its :Date: header"
        assert stated[1] == newest_row["date"], (
            f":Date: says {stated[1]} and the newest change is dated "
            f"{newest_row['date']}"
        )

    def test_the_only_reused_versions_are_the_known_collision(self, guide):
        """Fourteen rows answer to seven numbers, and it is not a typo.

        Measured 2026-09-21. Two §2.4 campaigns -- one over `addons/`
        (stock, point_of_sale, project, mrp, hr), one over the core packages
        (base, http, db, cli) -- each numbered its rows from 6.10, and both
        landed. The `addons` block sits between 6.26 and 6.25 and is the
        interloper: the core block is in descending order in its own place,
        and the guide's two prose citations of these numbers ("the converse
        of 6.16's reserved-row reading", "after 6.13 drained the abolished
        verbs") both resolve to it by proximity.

        Renumbering was measured and rejected, and Appendix D's own opening
        now records that: the seven rows need slots between 6.26 and 6.25 and
        there are none, so an integer re-sequence cascades over 32 rows --
        and five commit bodies cite these numbers, where a body cannot be
        amended on a shared branch. Each citation would then resolve to a
        DIFFERENT change rather than to nothing, which is worse than an
        ambiguity a reader can see.

        So this pins the damage instead: an eighth collision fails here, and
        so does a repair, the latter being the point at which this test and
        the note it guards should both go.
        """
        appendix = guide[guide.index("Appendix D — Document history") :]
        seen: dict[str, int] = {}
        for match in _ROW.finditer(appendix):
            seen[match["version"]] = seen.get(match["version"], 0) + 1
        reused = {v: n for v, n in seen.items() if n > 1}
        assert reused == dict.fromkeys(
            ("6.16", "6.15", "6.14", "6.13", "6.12", "6.11", "6.10"), 2
        ), (
            f"Appendix D's reused version numbers changed: {reused}. Either a "
            f"new collision landed, or the known one was repaired and this "
            f"test has done its job and should go"
        )

    def test_the_rows_descend_apart_from_that_one_block(self, guide):
        """One break, at the seam the collision made, and no other."""
        appendix = guide[guide.index("Appendix D — Document history") :]
        versions = [
            tuple(int(p) for p in m["version"].split("."))
            for m in _ROW.finditer(appendix)
        ]
        assert len(versions) > 1, "Appendix D parsed as a single row; the regex rotted"
        breaks = [
            (versions[i], versions[i + 1])
            for i in range(len(versions) - 1)
            if versions[i] < versions[i + 1]
        ]
        assert breaks == [((6, 10), (6, 25))], (
            f"Appendix D's ordering changed: {breaks}. Its first row is its "
            f"newest change only while it descends"
        )
