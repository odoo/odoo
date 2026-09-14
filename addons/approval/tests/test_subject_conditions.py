from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import add_category_approver, add_rule_step, new_trip_category


@tagged("post_install", "-at_install")
class TestSubjectConditions(common.TransactionCase):
    """Conditions that read the source document rather than the request.

    `approval.rule` historically compared only the four normalised figures the
    request carries (amount, quantity, date range, priority). These cover the
    two condition types that reach through `res_model`/`res_id` to the document
    the request was raised for.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Subject Approver",
                "login": "subject_approver",
                "email": "subject_approver@test.com",
            }
        )
        cls.extra_approver = cls.env["res.users"].create(
            {
                "name": "Subject Extra",
                "login": "subject_extra",
                "email": "subject_extra@test.com",
            }
        )
        cls.category = new_trip_category(cls.env)
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.company_partner = cls.env["res.partner"].create(
            {"name": "Subject Co", "is_company": True}
        )
        cls.person_partner = cls.env["res.partner"].create(
            {"name": "Subject Person", "is_company": False}
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "Subject Request",
            "category_id": self.category.id,
            "request_owner_id": self.env.ref("base.user_admin").id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def _domain_rule(self, domain, **kwargs):
        vals = {
            "name": "Company Partners Need Review",
            "condition_type": "domain",
            "subject_model_id": self.partner_model.id,
            "subject_domain": domain,
        }
        vals.update(kwargs)
        return add_rule_step(self.category, self.extra_approver, **vals)

    # -- domain conditions -------------------------------------------------

    def test_domain_condition_matching_document_adds_the_approver(self):
        self._domain_rule("[('is_company', '=', True)]")
        request = self._create_request(
            res_model="res.partner", res_id=self.company_partner.id
        )
        self.assertIn(self.extra_approver, request.approver_ids.mapped("user_id"))
        self.assertEqual(len(request.applied_rule_ids), 1)

    def test_domain_condition_non_matching_document_does_not(self):
        self._domain_rule("[('is_company', '=', True)]")
        request = self._create_request(
            res_model="res.partner", res_id=self.person_partner.id
        )
        self.assertNotIn(self.extra_approver, request.approver_ids.mapped("user_id"))
        self.assertFalse(request.applied_rule_ids)

    def test_domain_condition_ignores_a_request_with_no_source_document(self):
        self._domain_rule("[('is_company', '=', True)]")
        request = self._create_request()
        self.assertNotIn(self.extra_approver, request.approver_ids.mapped("user_id"))

    def test_domain_condition_ignores_a_source_document_of_another_model(self):
        """A rule scoped to res.partner must not fire on a res.users request."""
        self._domain_rule("[('is_company', '=', True)]")
        request = self._create_request(
            res_model="res.users", res_id=self.approver_user.id
        )
        self.assertNotIn(self.extra_approver, request.approver_ids.mapped("user_id"))

    def test_domain_condition_survives_a_deleted_source_document(self):
        self._domain_rule("[('is_company', '=', True)]")
        doomed = self.env["res.partner"].create({"name": "Doomed", "is_company": True})
        res_id = doomed.id
        doomed.unlink()
        request = self._create_request(res_model="res.partner", res_id=res_id)
        self.assertNotIn(self.extra_approver, request.approver_ids.mapped("user_id"))

    def test_domain_condition_walks_a_dotted_path(self):
        self.company_partner.write({"country_id": self.env.ref("base.be").id})
        self._domain_rule("[('country_id.code', '=', 'BE')]")
        request = self._create_request(
            res_model="res.partner", res_id=self.company_partner.id
        )
        self.assertIn(self.extra_approver, request.approver_ids.mapped("user_id"))

    # -- field_selection conditions ---------------------------------------

    def test_field_selection_condition_matches_on_the_stored_key(self):
        add_rule_step(
            self.category,
            self.extra_approver,
            name="Only Contacts",
            condition_type="field_selection",
            subject_model_id=self.partner_model.id,
            subject_field="type",
            subject_value="contact",
        )
        request = self._create_request(
            res_model="res.partner", res_id=self.company_partner.id
        )
        self.assertEqual(self.company_partner.type, "contact")
        self.assertIn(self.extra_approver, request.approver_ids.mapped("user_id"))

    def test_field_selection_condition_does_not_match_another_value(self):
        add_rule_step(
            self.category,
            self.extra_approver,
            name="Only Invoice Addresses",
            condition_type="field_selection",
            subject_model_id=self.partner_model.id,
            subject_field="type",
            subject_value="invoice",
        )
        request = self._create_request(
            res_model="res.partner", res_id=self.company_partner.id
        )
        self.assertNotIn(self.extra_approver, request.approver_ids.mapped("user_id"))

    # -- configuration-time validation ------------------------------------

    def test_a_domain_rule_without_a_source_model_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "name": "No Model",
                    "category_id": self.category.id,
                    "condition_type": "domain",
                    "subject_domain": "[('is_company', '=', True)]",
                }
            )

    def test_an_unparseable_domain_is_refused_at_configuration_time(self):
        with self.assertRaises(ValidationError):
            self._domain_rule("[('is_company', '=', ")

    def test_a_domain_naming_an_unknown_field_is_refused(self):
        """A typo would otherwise read as 'approval was not required'."""
        with self.assertRaises(ValidationError):
            self._domain_rule("[('is_compayn', '=', True)]")

    def test_a_dotted_path_through_an_unknown_field_is_refused(self):
        with self.assertRaises(ValidationError):
            self._domain_rule("[('country_id.no_such_field', '=', 'BE')]")

    def test_a_field_selection_rule_naming_an_unknown_field_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "name": "Bad Field",
                    "category_id": self.category.id,
                    "condition_type": "field_selection",
                    "subject_model_id": self.partner_model.id,
                    "subject_field": "not_a_field",
                    "subject_value": "x",
                }
            )

    def test_a_threshold_rule_still_needs_its_field_and_operator(self):
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "name": "Incomplete Threshold",
                    "category_id": self.category.id,
                    "condition_type": "threshold",
                    "threshold": 10,
                }
            )
