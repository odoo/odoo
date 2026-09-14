from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import ApprovalCommon, new_trip_category


@tagged("post_install", "-at_install")
class TestApprovalTiers(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_approver = cls.env["res.users"].create(
            {
                "name": "Default Approver",
                "login": "tier_default",
                "email": "tier_default@test.com",
            }
        )
        cls.director = cls.env["res.users"].create(
            {
                "name": "Director",
                "login": "tier_director",
                "email": "tier_director@test.com",
            }
        )
        cls.cfo = cls.env["res.users"].create(
            {
                "name": "CFO",
                "login": "tier_cfo",
                "email": "tier_cfo@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        cls.category.write(
            {
                "approver_ids": [(5, 0, 0)],
            }
        )
        cls.env["approval.category.approver"].create(
            {
                "category_id": cls.category.id,
                "user_id": cls.default_approver.id,
                "required": True,
                "sequence": 10,
            }
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "Tier Test",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def test_tier_threshold_max_must_exceed_min(self):
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "action_type": "set_approvers",
                    "condition_field": "amount",
                    "operator": "between",
                    "name": "Invalid Tier",
                    "category_id": self.category.id,
                    "threshold": 1000,
                    "threshold_max": 500,
                    "approver_ids": [(4, self.director.id)],
                }
            )

    def test_tier_zero_max_means_unlimited(self):
        tier = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "Unlimited",
                "category_id": self.category.id,
                "threshold": 10000,
                "threshold_max": 0,
                "approver_ids": [(4, self.cfo.id)],
            }
        )
        self.assertTrue(tier.id)

    def test_tier_no_overlap(self):
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "Standard",
                "category_id": self.category.id,
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [(4, self.default_approver.id)],
            }
        )
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "action_type": "set_approvers",
                    "condition_field": "amount",
                    "operator": "between",
                    "name": "Overlap",
                    "category_id": self.category.id,
                    "threshold": 500,
                    "threshold_max": 2000,
                    "approver_ids": [(4, self.director.id)],
                }
            )

    def test_tier_adjacent_ranges_ok(self):
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "Low",
                "category_id": self.category.id,
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [(4, self.default_approver.id)],
            }
        )
        tier2 = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "High",
                "category_id": self.category.id,
                "threshold": 1000,
                "threshold_max": 0,
                "approver_ids": [(4, self.director.id)],
            }
        )
        self.assertTrue(tier2.id)

    def test_matches_within_range(self):
        tier = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "Mid",
                "category_id": self.category.id,
                "threshold": 100,
                "threshold_max": 500,
                "approver_ids": [(4, self.director.id)],
            }
        )
        self.assertTrue(tier._compare(100, tier.threshold))
        self.assertTrue(tier._compare(250, tier.threshold))
        self.assertFalse(tier._compare(500, tier.threshold))
        self.assertFalse(tier._compare(50, tier.threshold))

    def test_matches_unlimited_range(self):
        tier = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "Top",
                "category_id": self.category.id,
                "threshold": 10000,
                "threshold_max": 0,
                "approver_ids": [(4, self.cfo.id)],
            }
        )
        self.assertTrue(tier._compare(10000, tier.threshold))
        self.assertTrue(tier._compare(999999, tier.threshold))
        self.assertFalse(tier._compare(9999, tier.threshold))

    def test_tier_replaces_default_approvers(self):
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "Director Level",
                "category_id": self.category.id,
                "threshold": 5000,
                "threshold_max": 0,
                "approver_ids": [(4, self.director.id), (4, self.cfo.id)],
            }
        )
        request = self._create_request(amount=8000)
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(self.director, approver_users)
        self.assertIn(self.cfo, approver_users)

    def test_tier_matches_after_currency_conversion(self):
        company = self.env.company
        company_ccy = company.currency_id
        other = self.env.ref("base.EUR")
        other.active = True
        self.env["res.currency.rate"].create(
            {
                "name": fields.Date.context_today(self.env.user),
                "currency_id": other.id,
                "company_id": company.id,
                "rate": 2.0,
            }
        )
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "FX Tier",
                "category_id": self.category.id,
                "currency_id": other.id,
                "threshold": 1000,
                "threshold_max": 0,
                "approver_ids": [(4, self.cfo.id)],
            }
        )
        matched = self._create_request(amount=600, currency_id=company_ccy.id)
        self.assertIn(self.cfo, matched.approver_ids.mapped("user_id"))
        below = self._create_request(amount=300, currency_id=company_ccy.id)
        below_users = below.approver_ids.mapped("user_id")
        self.assertIn(self.default_approver, below_users)
        self.assertNotIn(self.cfo, below_users)

    def test_no_tier_uses_default_approvers(self):
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "condition_field": "amount",
                "operator": "between",
                "name": "High Only",
                "category_id": self.category.id,
                "threshold": 50000,
                "threshold_max": 0,
                "approver_ids": [(4, self.director.id)],
            }
        )
        request = self._create_request(amount=100)
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(self.default_approver, approver_users)
        self.assertNotIn(self.director, approver_users)

    def test_no_tiers_configured_uses_defaults(self):
        request = self._create_request(amount=5000)
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(self.default_approver, approver_users)

    def test_which_band_wins_across_fields_is_stated_not_implied(self):
        amount_band = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Amount Band",
                "category_id": self.category.id,
                "condition_field": "amount",
                "sequence": 10,
                "threshold": 0,
                "threshold_max": 0,
                "approver_ids": [(4, self.director.id)],
            }
        )
        quantity_band = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Quantity Band",
                "category_id": self.category.id,
                "condition_field": "quantity",
                "sequence": 20,
                "threshold": 0,
                "threshold_max": 0,
                "approver_ids": [(4, self.cfo.id)],
            }
        )
        request = self._create_request(amount=500, quantity=10)
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(self.director, approver_users)
        self.assertNotIn(self.cfo, approver_users)
        self.assertIn(amount_band, request.applied_rule_ids)
        self.assertNotIn(quantity_band, request.applied_rule_ids)


@tagged("post_install", "-at_install")
class TestApprovalTiersAuditRegressions(ApprovalCommon):
    def test_amount_change_resyncs_tier_approvers(self):
        category = self._make_category(approvers=[self.approver_1])
        low_tier_approver = self.approver_1
        high_tier_approver = self.approver_2
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": f"Low {self.id()}",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [Command.link(low_tier_approver.id)],
                "approval_minimum": 1,
            },
        )
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": f"High {self.id()}",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 1000,
                "threshold_max": 0,
                "approver_ids": [Command.link(high_tier_approver.id)],
                "approval_minimum": 1,
            },
        )
        request = self._prepare_request(category, confirm=False, amount=100)
        self.assertEqual(request.approver_ids.user_id, low_tier_approver)

        request.write({"amount": 5000})
        self.assertEqual(
            request.approver_ids.user_id,
            high_tier_approver,
            "Approvers must be re-synced to the high tier immediately "
            "after the amount crosses the threshold, not only at confirm.",
        )

        request.action_confirm()
        self.assertEqual(request.approver_ids.user_id, high_tier_approver)

    def test_tier_approval_minimum_zero_rejected(self):
        category = self._make_category(approvers=[self.approver_1])
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "action_type": "set_approvers",
                    "operator": "between",
                    "name": f"Zero Minimum {self.id()}",
                    "category_id": category.id,
                    "condition_field": "amount",
                    "threshold": 0,
                    "threshold_max": 0,
                    "approver_ids": [Command.link(self.approver_1.id)],
                    "approval_minimum": 0,
                },
            )

    def test_tier_approval_minimum_above_approver_count_rejected(self):
        category = self._make_category(approvers=[self.approver_1])
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "action_type": "set_approvers",
                    "operator": "between",
                    "name": f"Impossible Minimum {self.id()}",
                    "category_id": category.id,
                    "condition_field": "amount",
                    "threshold": 0,
                    "threshold_max": 0,
                    "approver_ids": [Command.link(self.approver_1.id)],
                    "approval_minimum": 2,
                },
            )

    def test_tiers_same_range_different_companies_do_not_collide(self):
        company_a = self.env["res.company"].create({"name": f"Co A {self.id()}"})
        company_b = self.env["res.company"].create({"name": f"Co B {self.id()}"})
        self.approver_1.write({"company_ids": [(4, company_a.id), (4, company_b.id)]})
        category = self._make_category(approvers=[self.approver_1], company_id=False)

        tier_a = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Standard",
                "category_id": category.id,
                "company_id": company_a.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [Command.link(self.approver_1.id)],
            },
        )
        tier_b = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Standard",
                "category_id": category.id,
                "company_id": company_b.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [Command.link(self.approver_1.id)],
            },
        )
        self.assertTrue(tier_a.exists())
        self.assertTrue(tier_b.exists())

    def test_tiers_same_range_same_company_still_collide(self):
        company_a = self.env["res.company"].create({"name": f"Co A {self.id()}"})
        self.approver_1.write({"company_ids": [(4, company_a.id)]})
        category = self._make_category(approvers=[self.approver_1], company_id=False)
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Standard",
                "category_id": category.id,
                "company_id": company_a.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [Command.link(self.approver_1.id)],
            },
        )
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "action_type": "set_approvers",
                    "operator": "between",
                    "name": "Overlapping",
                    "category_id": category.id,
                    "company_id": company_a.id,
                    "condition_field": "amount",
                    "threshold": 500,
                    "threshold_max": 1500,
                    "approver_ids": [Command.link(self.approver_1.id)],
                },
            )

    def test_tiers_global_tier_still_collides_with_company_tier(self):
        company_a = self.env["res.company"].create({"name": f"Co A {self.id()}"})
        category = self._make_category(approvers=[self.approver_1])
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Global",
                "category_id": category.id,
                "company_id": False,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [Command.link(self.approver_1.id)],
            },
        )
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "action_type": "set_approvers",
                    "operator": "between",
                    "name": "Company-specific",
                    "category_id": category.id,
                    "company_id": company_a.id,
                    "condition_field": "amount",
                    "threshold": 500,
                    "threshold_max": 1500,
                    "approver_ids": [Command.link(self.approver_1.id)],
                },
            )

    def test_m9_tier_overlap_detected_on_simultaneous_activation(self):
        category = self._make_category(approvers=[self.approver_1])
        tier_1 = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": f"Tier 1 {self.id()}",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 1000,
                "approver_ids": [Command.link(self.approver_1.id)],
                "active": False,
            },
        )
        tier_2 = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": f"Tier 2 {self.id()}",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 500,
                "threshold_max": 1500,
                "approver_ids": [Command.link(self.approver_1.id)],
                "active": False,
            },
        )
        with self.assertRaises(ValidationError):
            (tier_1 | tier_2).write({"active": True})

    def test_invalid_minimum_false_positive_fixed_by_tier(self):
        category = self._make_category(approval_minimum=2)
        self.assertTrue(category.invalid_minimum)

        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Two Approvers",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 0,
                "approver_ids": [
                    Command.link(self.approver_1.id),
                    Command.link(self.approver_2.id),
                ],
                "approval_minimum": 2,
            },
        )
        category.invalidate_recordset(["invalid_minimum"])
        self.assertFalse(
            category.invalid_minimum,
            "A tier providing enough approvers must clear the "
            "category-level false-positive warning.",
        )

    def test_invalid_minimum_still_flags_when_no_source_is_enough(self):
        category = self._make_category(
            approvers=[self.approver_1],
            approval_minimum=1,
        )
        self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "One Approver",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 0,
                "threshold_max": 0,
                "approver_ids": [Command.link(self.approver_1.id)],
                "approval_minimum": 1,
            },
        )
        category.approval_minimum = 5
        self.assertTrue(category.invalid_minimum)


@tagged("post_install", "-at_install")
class TestReplacementMatchingIsExtensible(ApprovalCommon):
    def test_an_unknown_condition_field_does_not_break_matching(self):
        category = self._make_category(
            name="Extensible Tiers",
            approvers=[(self.approver_1, False, 10)],
        )
        tier = self.env["approval.rule"].create(
            {
                "action_type": "set_approvers",
                "operator": "between",
                "name": "Extension Tier",
                "category_id": category.id,
                "condition_field": "amount",
                "threshold": 10.0,
                "threshold_max": 20.0,
                "approver_ids": [(6, 0, [self.approver_2.id])],
                "approval_minimum": 1,
            },
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE approval_rule SET condition_field = 'weight' WHERE id = %s",
            [tier.id],
        )
        self.env.invalidate_all()

        request = self._prepare_request(category, confirm=False, amount=-5.0)

        self.assertTrue(
            request.approver_ids,
            "The request must still get its category approvers.",
        )


@tagged("post_install", "-at_install")
class TestConfigConstraintsAreBatched(ApprovalCommon):
    def _count_selects(self, table, action):
        seen = []
        cursor = self.env.cr
        original = type(cursor).execute

        def spy(self_cr, query, *args, **kwargs):
            text = str(query)
            if f'FROM "{table}"' in text and "SELECT" in text.upper():
                seen.append(text)
            return original(self_cr, query, *args, **kwargs)

        self.patch(type(cursor), "execute", spy)
        action()
        self.env.flush_all()
        return len(seen)

    def test_creating_many_tiers_does_not_scale_the_constraint_queries(self):
        category = self._make_category("Batched Tiers", approvers=[self.approver_1])
        self.env.flush_all()

        def create(count, offset):
            def _do():
                self.env["approval.rule"].create(
                    [
                        {
                            "action_type": "set_approvers",
                            "operator": "between",
                            "name": f"T{offset}{index}",
                            "category_id": category.id,
                            "condition_field": "amount",
                            "threshold": (offset + index) * 1000,
                            "threshold_max": (offset + index + 1) * 1000,
                            "approver_ids": [(6, 0, [self.approver_2.id])],
                            "approval_minimum": 1,
                        }
                        for index in range(count)
                    ],
                )

            return _do

        eight = self._count_selects("approval_rule", create(8, 0))
        sixteen = self._count_selects("approval_rule", create(16, 100))

        self.assertLess(eight, 8, "8 tiers still cost a query each: %d" % eight)
        self.assertLessEqual(
            sixteen,
            eight + 2,
            "the constraint still scales with batch size: %d for 8, %d for 16"
            % (eight, sixteen),
        )
