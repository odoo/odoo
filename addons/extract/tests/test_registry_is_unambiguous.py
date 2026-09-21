# `get_readers` orders by `reader_rank` -- cost, then whether the reader defers
# to its peers -- and `_derive` falls through a reader that answered nothing, so
# the registry decides between readers that DIFFER. Neither decides between two
# claiming one mimetype for one representation at one rank: `sorted` is stable,
# so module load order wins and nothing declares it.
# `extract` reads a PDF with pymupdf and `attachment_indexation` with
# pdfminer.six, which is the pair this exists for.

from collections import defaultdict

from odoo.libs.documents import (
    TEXT,
    BaseReader,
    reader_rank,
    register_reader,
    registered_readers,
    registered_writers,
    unregister_reader,
)
from odoo.tests.common import BaseCase, tagged


def reader_claims(readers):
    """Every (mimetype, representation, cost) more than one reader answers for."""
    claims = defaultdict(list)
    for reader in readers:
        for mimetype in reader.mimetypes:
            for representation in reader.yields:
                claims[(mimetype, representation, reader_rank(reader))].append(
                    reader.name
                )
    return {key: names for key, names in claims.items() if len(names) > 1}


def writer_claims(writers):
    claims = defaultdict(list)
    for writer in writers:
        claims[(writer.mimetype, writer.consumes)].append(writer.name)
    return {key: names for key, names in claims.items() if len(names) > 1}


@tagged("post_install", "-at_install")
class TestRegistryIsUnambiguous(BaseCase):
    # `post_install`: the registry fills as modules import, so an at-install run
    # would assert over whichever part of the graph had loaded and pass by
    # seeing less.

    def test_no_two_readers_claim_one_mimetype_at_one_cost(self):
        ambiguous = reader_claims(registered_readers())

        self.assertFalse(
            ambiguous,
            "these readers are chosen by module load order:\n  "
            + "\n  ".join(
                f"{mimetype} {representation} at rank {rank}: "
                + ", ".join(sorted(names))
                for (mimetype, representation, rank), names in sorted(ambiguous.items())
            )
            + "\nGive one of them a higher cost, let one defer to the other, "
            "or decide which owns the format.",
        )

    def test_no_two_writers_claim_one_mimetype(self):
        # Not symmetry for its own sake: a writer declares no cost,
        # `get_writers` sorts by nothing and `Document.of` takes the first, with
        # no fall-through because a writer that cannot write cannot say so.
        ambiguous = writer_claims(registered_writers())

        self.assertFalse(
            ambiguous,
            "these writers are chosen by module load order:\n  "
            + "\n  ".join(
                f"{mimetype} from {representation}: " + ", ".join(sorted(names))
                for (mimetype, representation), names in sorted(ambiguous.items())
            ),
        )

    def test_the_check_is_not_looking_at_an_empty_registry(self):
        # `pdf_text` specifically, not a count: it proves the enumeration
        # reaches past the library into the addon this test ships in.
        self.assertGreaterEqual(len(registered_readers()), 6)
        self.assertGreaterEqual(len(registered_writers()), 6)
        self.assertIn("pdf_text", [r.name for r in registered_readers()])

    def test_a_collision_is_actually_detected(self):
        # Green is also what a broken check looks like.
        clash = type(
            "_Pdfminer",
            (BaseReader,),
            {
                "name": "test_second_pdf_text",
                "mimetypes": frozenset({"application/pdf"}),
                "yields": (TEXT,),
                "cost": 0,
                "read": lambda self, document: "",
            },
        )()
        register_reader(clash)
        self.addCleanup(unregister_reader, clash)

        found = reader_claims(registered_readers())

        self.assertIn(("application/pdf", TEXT, (0, False)), found)
        clashing = found[("application/pdf", TEXT, (0, False))]
        self.assertIn("test_second_pdf_text", clashing)
        self.assertIn("pdf_text", clashing)

    def test_a_reader_that_defers_is_not_a_collision(self):
        deferring = type(
            "_DeferringPdf",
            (BaseReader,),
            {
                "name": "test_deferring_pdf_text",
                "mimetypes": frozenset({"application/pdf"}),
                "yields": (TEXT,),
                "cost": 0,
                "defers": True,
                "read": lambda self, document: "",
            },
        )()
        register_reader(deferring)
        self.addCleanup(unregister_reader, deferring)

        self.assertNotIn(
            ("application/pdf", TEXT, (0, False)), reader_claims(registered_readers())
        )
