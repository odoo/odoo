import contextlib

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.extract.tools import FREE, BaseExtractor
from odoo.addons.extract.tools import extractors as registry


class _Stub(BaseExtractor):
    name = "cv_test_stub"
    doc_types = ("resume",)
    needs = ("text",)
    cost = FREE
    confidence = 0.9

    def __init__(self, values):
        self._values = values

    def extract(self, source, doc_type, wanted, env=None):
        return dict(self._values) if self._values else None


@contextlib.contextmanager
def _only(extractor):
    saved = dict(registry._EXTRACTORS)
    registry._EXTRACTORS.clear()
    try:
        registry.register_extractor(extractor)
        yield
    finally:
        registry._EXTRACTORS.clear()
        registry._EXTRACTORS.update(saved)


_READ = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+52 55 1234 5678",
}


@tagged("post_install", "-at_install")
class TestApplicantExtraction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job = cls.env["hr.job"].create({"name": "Analyst"})

    def _applicant(self, **values):
        applicant = self.env["hr.applicant"].create({"job_id": self.job.id, **values})
        self.env["ir.attachment"].create(
            {
                "name": "cv.txt",
                "res_model": "hr.applicant",
                "res_id": applicant.id,
                "mimetype": "text/plain",
                "raw": b"a curriculum vitae with words on it",
            }
        )
        return applicant

    def test_it_fills_the_header_from_the_cv(self):
        with _only(_Stub(_READ)):
            applicant = self._applicant()

            applicant.action_extract_document()

        self.assertEqual(applicant.partner_name, "Ada Lovelace")
        self.assertEqual(applicant.email_from, "ada@example.com")
        self.assertEqual(applicant.phone_ids.number, "+52 55 1234 5678")
        self.assertEqual(applicant.extract_state, "done")

    def test_it_does_not_overwrite_what_a_recruiter_typed(self):
        with _only(_Stub(_READ)):
            applicant = self._applicant(partner_name="the name I was told")

            applicant.action_extract_document()

        self.assertEqual(applicant.partner_name, "the name I was told")
        self.assertEqual(applicant.email_from, "ada@example.com")

    def test_it_keeps_which_reader_produced_each_value(self):
        with _only(_Stub(_READ)):
            applicant = self._applicant()

            applicant.action_extract_document()

        self.assertEqual(
            applicant.extract_result["full_name"]["source"], "cv_test_stub"
        )

    def test_a_new_applicant_can_be_read(self):
        applicant = self._applicant()

        self.assertTrue(applicant.extract_can_be_read)

    def test_an_applicant_past_the_first_stage_is_not_read(self):
        applicant = self._applicant()
        later = self.env["hr.recruitment.stage"].search(
            [("fold", "=", False)], order="sequence desc", limit=1
        )
        applicant.stage_id = later

        self.assertFalse(applicant.extract_can_be_read)
        with self.assertRaises(UserError):
            applicant.action_extract_document()

    def test_the_document_type_is_a_resume_whatever_the_stage(self):
        applicant = self._applicant()
        later = self.env["hr.recruitment.stage"].search(
            [("fold", "=", False)], order="sequence desc", limit=1
        )
        applicant.stage_id = later

        self.assertEqual(applicant._get_extract_document_type(), "resume")

    def test_reading_is_not_offered_again_once_it_is_done(self):
        with _only(_Stub(_READ)):
            applicant = self._applicant()

            applicant.action_extract_document()

        self.assertEqual(applicant.extract_state, "done")
        self.assertFalse(applicant.extract_can_be_read)

    def test_a_blank_phone_creates_no_phone_record(self):
        """A read the model was not sure of must not leave a numberless
        ``phone.number`` behind: the target is a relation, so an empty string is
        not simply an empty column."""
        before = self.env["phone.number"].search_count([])
        with _only(_Stub({**_READ, "phone": "   "})):
            applicant = self._applicant()

            applicant.action_extract_document()

        self.assertFalse(applicant.phone_ids)
        self.assertEqual(self.env["phone.number"].search_count([]), before)

    def test_a_phone_the_database_already_holds_is_linked_not_duplicated(self):
        existing = self.env["phone.number"].create({"number": "+52 55 1234 5678"})
        before = self.env["phone.number"].search_count([])
        with _only(_Stub(_READ)):
            applicant = self._applicant()

            applicant.action_extract_document()

        self.assertEqual(applicant.phone_ids, existing)
        self.assertEqual(self.env["phone.number"].search_count([]), before)

    def test_it_does_not_overwrite_a_phone_a_recruiter_typed(self):
        typed = self.env["phone.number"].create({"number": "+32 470 00 00 00"})
        with _only(_Stub(_READ)):
            applicant = self._applicant(phone_ids=[(6, 0, typed.ids)])

            applicant.action_extract_document()

        self.assertEqual(applicant.phone_ids, typed)

    def test_correcting_the_phone_records_the_number_not_a_command_list(self):
        with _only(_Stub(_READ)):
            applicant = self._applicant()
            applicant.action_extract_document()
        corrected = self.env["phone.number"].create({"number": "+32 470 11 22 33"})

        applicant.write({"phone_ids": [(6, 0, corrected.ids)]})

        recorded = (applicant.extract_corrections or {}).get("phone")
        self.assertTrue(recorded, applicant.extract_corrections)
        self.assertEqual(recorded["read"], "+52 55 1234 5678")
        self.assertEqual(recorded["corrected_to"], "+32 470 11 22 33")

    def test_clearing_the_phone_records_no_correction(self):
        """An uncomparable write is not a correction to ``None``."""
        with _only(_Stub(_READ)):
            applicant = self._applicant()
            applicant.action_extract_document()

        applicant.write({"phone_ids": [(5, 0, 0)]})

        self.assertFalse((applicant.extract_corrections or {}).get("phone"))
