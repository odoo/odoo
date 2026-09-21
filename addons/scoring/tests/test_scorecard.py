from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "scoring")
class TestScorecard(TransactionCase):
    def test_every_dimension_code_resolves_to_a_hook_on_its_host(self):
        # A module that ships a dimension record without the hook its code
        # names is red at install, the way a HOOT file without a runner is.
        dimensions = (
            self.env["scorecard.dimension"].with_context(active_test=False).search([])
        )
        for dimension in dimensions:
            host = self.env[dimension.scorecard_id.res_model]
            self.assertTrue(
                hasattr(host, f"_score_observe_{dimension.code}")
                or hasattr(host, f"_score_rows_{dimension.code}"),
                f"{dimension.scorecard_id.res_model} answers no dimension "
                f"{dimension.code!r}",
            )
            if dimension.kind == "catalog":
                self.assertTrue(
                    dimension.catalog_model in self.env
                    or hasattr(host, f"_score_ceiling_{dimension.code}"),
                    f"{dimension.code!r} is a catalog dimension with no catalog",
                )

    def test_every_host_is_offered_and_abstract_models_are_not(self):
        offered = dict(self.env["scorecard"]._selection_res_model())
        self.assertNotIn("mixin.scored", offered)
        for name in offered:
            self.assertTrue(
                isinstance(self.env[name], self.env.registry["mixin.scored"]), name
            )

    def test_a_dimension_band_may_start_below_zero_and_may_not_overlap(self):
        host = next(iter(dict(self.env["scorecard"]._selection_res_model())), None)
        if host is None:
            self.skipTest("no scored model installed")
        scorecard = self.env["scorecard"].create(
            {"name": "Probe", "res_model": host, "active": False}
        )
        code = [
            value
            for value, _label in self.env["scorecard.dimension"]
            ._fields["code"]
            ._description_selection(self.env)
        ]
        if not code:
            self.skipTest("no dimension code registered")
        dimension = self.env["scorecard.dimension"].create(
            {
                "scorecard_id": scorecard.id,
                "code": code[0],
                "kind": "measure",
                "weight": 40.0,
            }
        )
        early = self.env["scorecard.dimension.band"].create(
            {
                "dimension_id": dimension.id,
                "min_value": -100000.0,
                "max_value": 0.1,
                "points": 100.0,
            }
        )
        self.assertTrue(early._is_covering(-3.0))
        self.assertTrue(early._is_covering(0.0))
        self.assertFalse(early._is_covering(0.1))
        with self.assertRaises(ValidationError):
            self.env["scorecard.dimension.band"].create(
                {
                    "dimension_id": dimension.id,
                    "min_value": 0.0,
                    "max_value": 15.1,
                    "points": 80.0,
                }
            )

    def test_one_active_scorecard_per_model_and_company(self):
        host = next(iter(dict(self.env["scorecard"]._selection_res_model())), None)
        if host is None:
            self.skipTest("no scored model installed")
        Scorecard = self.env["scorecard"]
        shared = Scorecard._for(host, self.env.company)
        if not shared:
            shared = Scorecard.create({"name": "Shared", "res_model": host})
        with self.assertRaises(ValidationError):
            Scorecard.create(
                {"name": "Twin", "res_model": host, "company_id": shared.company_id.id}
            )
        company = self.env["res.company"].create({"name": "Scored Co"})
        own = Scorecard.create(
            {"name": "Own", "res_model": host, "company_id": company.id}
        )
        self.assertEqual(Scorecard._for(host, company), own)
        self.assertEqual(Scorecard._for(host, self.env.company), shared)
