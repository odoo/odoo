import re
from datetime import timedelta

from odoo import fields
from odoo.tests import common, tagged

from .common import ApprovalCommon, add_category_approver, add_rule_step, pool_step


@tagged("post_install", "-at_install")
class TestApproverComputation(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self.env.ref("base.user_admin")
        self.category_user = self.env["res.users"].create(
            {
                "name": "Category Approver",
                "login": "cat_approver",
                "email": "cat@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.group_user = self.env["res.users"].create(
            {
                "name": "Group Member",
                "login": "group_member",
                "email": "group@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.duplicate_user = self.env["res.users"].create(
            {
                "name": "Duplicate User",
                "login": "dup_user",
                "email": "dup@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.manual_user = self.env["res.users"].create(
            {
                "name": "Manual Approver",
                "login": "manual_approver",
                "email": "manual@test.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        self.approval_group = self.env["res.groups"].create(
            {
                "name": "Test Approver Group",
                "user_ids": [(6, 0, [self.group_user.id, self.duplicate_user.id])],
            }
        )

    def test_compute_approver_ids_from_category_only(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0013",
                "name": "Test Category Only",
                "approval_minimum": 1,
            }
        )

        add_category_approver(category, self.category_user, required=True, sequence=10)
        add_category_approver(category, self.group_user, required=False, sequence=20)

        request = self.env["approval.request"].create(
            {
                "name": "Test Request",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.assertEqual(len(request.approver_ids), 2)

        category_approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.category_user
        )
        self.assertTrue(category_approver.required)
        self.assertEqual(category_approver.sequence, 10)

        group_approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.group_user
        )
        self.assertFalse(group_approver.required)
        self.assertEqual(group_approver.sequence, 20)

    def test_compute_approver_ids_preserves_manually_added_approvers(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0014",
                "name": "Test Manual Approvers",
                "approval_minimum": 1,
            }
        )

        add_category_approver(category, self.category_user, required=True, sequence=10)

        request = self.env["approval.request"].create(
            {
                "name": "Test Manual Add",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.env["approval.approver"].create(
            {
                "user_id": self.manual_user.id,
                "request_id": request.id,
                "flow_state": "new",
            }
        )

        request._sync_approvers()

        manual_approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.manual_user
        )
        self.assertTrue(manual_approver, "Manual approver should be preserved")
        self.assertEqual(
            manual_approver.sequence, 10, "a manual row keeps its own sequence"
        )
        self.assertFalse(
            manual_approver.required,
            "Manual approver should not be required by default",
        )

    def test_compute_approver_ids_manual_approver_highest_sequence(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0015",
                "name": "Test Manual Sequence",
                "approval_minimum": 1,
            }
        )

        add_category_approver(category, self.category_user, required=True, sequence=10)

        request = self.env["approval.request"].create(
            {
                "name": "Test Manual Highest",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.env["approval.approver"].create(
            {
                "user_id": self.manual_user.id,
                "request_id": request.id,
                "flow_state": "new",
            }
        )

        request._sync_approvers()

        approvers = request.approver_ids.sorted(lambda a: (a.sequence, a.id))
        self.assertEqual(approvers[0].user_id, self.category_user)
        self.assertEqual(approvers[-1].user_id, self.manual_user)
        self.assertEqual(
            approvers[-1].sequence, 10, "a manual row keeps its own sequence"
        )

    def test_compute_approver_ids_category_change_updates_approvers(self):
        category1 = self.env["approval.category"].create(
            {
                "sequence_code": "SC0017",
                "name": "Category 1",
                "approval_minimum": 1,
            }
        )
        category2 = self.env["approval.category"].create(
            {
                "sequence_code": "SC0018",
                "name": "Category 2",
                "approval_minimum": 1,
            }
        )

        add_category_approver(category1, self.category_user, required=True)
        add_category_approver(category2, self.group_user, required=True)

        request = self.env["approval.request"].create(
            {
                "name": "Test Category Change",
                "request_owner_id": self.admin_user.id,
                "category_id": category1.id,
            }
        )

        self.assertEqual(len(request.approver_ids), 1)
        self.assertEqual(request.approver_ids.user_id, self.category_user)

        request.category_id = category2

        self.assertEqual(len(request.approver_ids), 1)
        self.assertEqual(
            request.approver_ids.user_id,
            self.group_user,
            "Approvers should update when category changes",
        )

    def test_compute_approver_ids_handles_empty_category_approvers(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0019",
                "name": "Empty Category",
                "approval_minimum": 1,
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test Empty Category",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.assertEqual(len(request.approver_ids), 0)

    def test_compute_approver_ids_merges_category_and_manual_sequence(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0020",
                "name": "Test Category+Manual Duplicate",
                "approval_minimum": 1,
            }
        )

        add_category_approver(category, self.duplicate_user, required=True, sequence=10)

        request = self.env["approval.request"].create(
            {
                "name": "Test Duplicate Category+Manual",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )
        request._sync_approvers()

        dup_approvers = request.approver_ids.filtered(
            lambda a: a.user_id == self.duplicate_user
        )
        self.assertEqual(
            len(dup_approvers),
            1,
            "User should appear only once across category and manual sources",
        )
        self.assertEqual(
            dup_approvers.sequence,
            10,
            "Category sequence (10) wins over the manual default (1000)",
        )

    def test_compute_approver_ids_recomputation_on_save(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0021",
                "name": "Test Recomputation",
                "approval_minimum": 1,
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test Recompute",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.assertEqual(len(request.approver_ids), 0)

        category._add_approver(self.category_user, required=True)

        request.invalidate_recordset(["approver_ids"])
        request._sync_approvers()

        self.assertEqual(len(request.approver_ids), 1)
        self.assertEqual(request.approver_ids.user_id, self.category_user)

    def test_compute_approver_ids_every_member_of_a_group_step(self):
        many_users = self.env["res.users"].create(
            [
                {
                    "name": f"User {i}",
                    "login": f"user_{i}",
                    "email": f"user{i}@test.com",
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
                for i in range(10)
            ]
        )

        large_group = self.env["res.groups"].create(
            {
                "name": "Large Test Group",
                "user_ids": [(6, 0, many_users.ids)],
            }
        )

        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0022",
                "name": "Test Many Group Members",
                "approval_minimum": 1,
                "step_ids": pool_step([], minimum=1, group_id=large_group.id),
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test Many Members Request",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.assertEqual(
            len(request.approver_ids),
            len(large_group.all_user_ids),
            "Every group member should become an approver",
        )
        user_ids = request.approver_ids.mapped("user_id").ids
        self.assertEqual(
            len(user_ids),
            len(set(user_ids)),
            "All approver user_ids should be unique",
        )

    def test_compute_approver_ids_group_step_single_pass(self):
        category = self.env["approval.category"].create(
            {
                "sequence_code": "SC0023",
                "name": "Test Single Pass",
                "approval_minimum": 1,
                "step_ids": pool_step([], minimum=1, group_id=self.approval_group.id),
            }
        )

        request = self.env["approval.request"].create(
            {
                "name": "Test Single Pass",
                "request_owner_id": self.admin_user.id,
                "category_id": category.id,
            }
        )

        self.assertEqual(len(request.approver_ids), 2)
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(self.group_user, approver_users)
        self.assertIn(self.duplicate_user, approver_users)
        self.assertTrue(
            all(a.state == "new" for a in request.approver_ids),
            "All approvers should have state='new'",
        )


@tagged("post_install", "-at_install")
class TestApproverComputationAuditRegressions(ApprovalCommon):
    def test_category_approver_removal_visible_to_same_transaction_sync(self):
        category = self._make_category(approvers=[self.approver_1])
        request = self._prepare_request(category, confirm=False)

        self.assertIn(self.approver_1, request.approver_ids.user_id)

        category.step_ids.member_ids.unlink()
        request.sudo()._sync_approvers()
        request.invalidate_recordset(["approver_ids"])

        self.assertNotIn(
            self.approver_1,
            request.approver_ids.user_id,
            "A re-sync must see the removal within the same transaction, "
            "not a stale pre-removal snapshot. This used to be memoised "
            "per (transaction, company) in env.cr.cache with hand-rolled "
            "invalidation on the child model; the set is now read straight "
            "off the prefetched category one2many, so there is nothing to "
            "go stale.",
        )


@tagged("post_install", "-at_install")
class TestManualApproverHeuristic(ApprovalCommon):
    def test_manual_approver_survives_when_user_is_category_approver_elsewhere(self):
        cat_y = self._make_category(name="M8 Y", approvers=[self.approver_2])
        self._make_category(name="M8 X", approvers=[self.approver_1])

        request = self._prepare_request(cat_y, confirm=False)

        self.env["approval.approver"].sudo().with_context(
            approver_ids_computation=True,
        ).create(
            {
                "request_id": request.id,
                "user_id": self.approver_1.id,
                "sequence": 1000,
                "source_synced": False,
            }
        )

        request.sudo()._sync_approvers()
        request.invalidate_recordset(["approver_ids"])

        self.assertIn(
            self.approver_1,
            request.approver_ids.mapped("user_id"),
            "The managed-approver backstop must cover THIS request's "
            "category, not every category in the company. approver_1 is "
            "configured on an unrelated category (M8 X) and was added to "
            "this one by hand, so no automated source on this request ever "
            "produced them and nothing may delete them. Wiping them was the "
            "company-wide heuristic's documented limitation, closed in "
            "19.0.1.0.22 — the same narrowing the tier and rule legs got.",
        )

    def test_manual_approver_still_wiped_when_own_category_lists_them(self):
        category = self._make_category(name="M8 Own", approvers=[self.approver_2])
        request = self._prepare_request(category, confirm=False)

        category._add_approver(self.approver_1)
        request.sudo()._sync_approvers()
        request.invalidate_recordset(["approver_ids"])
        self.assertIn(
            self.approver_1,
            request.approver_ids.mapped("user_id"),
            "the category now lists approver_1, so a re-sync injects the row",
        )

        category.step_ids.member_ids.filtered(
            lambda member: member.user_id == self.approver_1,
        ).unlink()
        request.sudo()._sync_approvers()
        request.invalidate_recordset(["approver_ids"])

        self.assertNotIn(
            self.approver_1,
            request.approver_ids.mapped("user_id"),
            "Narrowing the backstop must not resurrect phantom approvers: a "
            "row this request's OWN category produced and then stopped "
            "producing is still an orphan and must be deleted.",
        )


@tagged("post_install", "-at_install")
class TestApproverSyncTriggerFields(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.director = cls.env["res.users"].create(
            {
                "name": "Director",
                "login": "trigger_director",
                "email": "trigger.director@test.com",
            },
        )

    def _category_with_rule(self, condition_field, operator, threshold, **cat_vals):
        category = self._make_category(
            name=f"Trigger {condition_field}",
            approvers=[(self.approver_1, False, 10)],
            **cat_vals,
        )
        add_rule_step(
            category,
            self.director,
            name=f"Escalate on {condition_field}",
            condition_field=condition_field,
            operator=operator,
            threshold=threshold,
        )
        return category

    def test_trigger_fields_cover_every_rule_condition_field(self):
        triggers = self.env["approval.request"]._get_fields_approver_sync_trigger()
        rule = self.env["approval.rule"]
        for condition_field in dict(
            rule._fields["condition_field"].selection,
        ):
            self.assertIn(
                condition_field,
                rule._CONDITION_FIELD_DEPENDS,
                f"condition_field {condition_field!r} declares no request "
                f"fields in _CONDITION_FIELD_DEPENDS, so editing its inputs "
                f"on a draft will not re-sync the approvers.",
            )
            for dependency in rule._CONDITION_FIELD_DEPENDS[condition_field]:
                self.assertIn(dependency, triggers)

    def test_priority_change_resyncs_approvers(self):
        category = self._category_with_rule("priority", "gte", 2)
        request = self._prepare_request(category, confirm=False)
        self.assertNotIn(self.director, request.approver_ids.user_id)

        request.write({"priority": "3"})

        self.assertIn(
            self.director,
            request.approver_ids.user_id,
            "Raising a draft to Urgent must pull in the rule's approver.",
        )

    def test_date_range_change_resyncs_approvers(self):
        category = self._category_with_rule("date_range_days", "gt", 5)
        request = self._prepare_request(category, confirm=False)

        request.write(
            {
                "date_start": "2026-01-01 00:00:00",
                "date_end": "2026-01-20 00:00:00",
            },
        )

        self.assertIn(self.director, request.approver_ids.user_id)

    def test_currency_change_resyncs_the_steps(self):
        usd = self.env.ref("base.USD")
        mxn = self.env.ref("base.MXN")
        (usd | mxn).sudo().write({"active": True})
        self.env["res.currency.rate"].sudo().create(
            {
                "currency_id": mxn.id,
                "company_id": self.env.company.id,
                "name": fields.Date.today() - timedelta(days=1),
                "rate": 20.0,
            },
        )
        category = self._make_category(name="Trigger currency")
        for name, user, low, high in (
            ("small", self.approver_1, 0.0, 1000.0),
            ("big", self.director, 1000.0, 0.0),
        ):
            add_rule_step(
                category,
                user,
                name=name,
                currency_id=usd.id,
                condition_field="amount",
                operator="between",
                threshold=low,
                threshold_max=high,
            )

        request = self._prepare_request(
            category, confirm=False, currency_id=mxn.id, amount=10000.0
        )
        self.assertEqual(request.approver_ids.user_id, self.approver_1)

        request.write({"currency_id": usd.id})

        self.assertEqual(
            request.approver_ids.user_id,
            self.director,
            "Switching the draft's currency crosses a tier boundary and "
            "must re-route the approvers.",
        )

    def test_desired_approvers_step_performs_no_writes(self):
        category = self._category_with_rule("priority", "gte", 2)
        request = self._prepare_request(category, confirm=False, priority="3")
        rule = self.env["approval.rule"].search([("category_id", "=", category.id)])
        request.sudo().write({"applied_rule_ids": [(5, 0, 0)]})
        self.env.flush_all()

        result = request._get_desired_approvers()

        self.assertFalse(
            request.applied_rule_ids,
            "_get_desired_approvers must not write applied_rule_ids; "
            "the caller persists what it returns.",
        )
        self.assertEqual(
            result.matched_rules,
            rule,
            "It must hand the matched rules back so the caller can "
            "persist them without evaluating every rule a second time.",
        )


@tagged("post_install", "-at_install")
class TestApproverSyncBatchesRowWrites(ApprovalCommon):
    def _count_approver_inserts(self, func):
        inserts = []
        cursor_cls = type(self.env.cr)
        original = cursor_cls.execute

        def counting(cr_self, query, params=None, log_exceptions=True):
            text = getattr(query, "code", None) or str(query)
            if re.match(r'\s*INSERT INTO "?approval_approver"?\s*\(', text):
                inserts.append(text)
            if params is not None:
                return original(cr_self, query, params, log_exceptions)
            return original(cr_self, query)

        self.patch(cursor_cls, "execute", counting)
        func()
        self.env.flush_all()
        return len(inserts)

    def test_creating_many_requests_issues_one_approver_insert(self):
        category = self._make_category(
            name="Batched Sync",
            approvers=[self.approver_1, self.approver_2],
        )

        def create_twenty():
            self.env["approval.request"].create(
                [
                    {
                        "category_id": category.id,
                        "request_owner_id": self.owner_user.id,
                    }
                    for _ in range(20)
                ],
            )

        inserts = self._count_approver_inserts(create_twenty)

        self.assertLessEqual(
            inserts,
            1,
            f"Creating 20 requests issued {inserts} INSERTs into "
            f"approval_approver; the whole batch's rows must go in one.",
        )

    def test_a_mixed_batch_still_gets_per_request_approvers(self):
        cat_a = self._make_category(name="Batch Cat A", approvers=[self.approver_1])
        cat_b = self._make_category(
            name="Batch Cat B",
            approvers=[self.approver_2, self.manager_user],
        )

        requests = self.env["approval.request"].create(
            [
                {"category_id": cat_a.id, "request_owner_id": self.owner_user.id},
                {"category_id": cat_b.id, "request_owner_id": self.owner_user.id},
                {"category_id": cat_a.id, "request_owner_id": self.owner_user.id},
            ],
        )
        self.env.flush_all()

        self.assertEqual(requests[0].approver_ids.user_id, self.approver_1)
        self.assertEqual(
            requests[1].approver_ids.user_id,
            self.approver_2 | self.manager_user,
        )
        self.assertEqual(requests[2].approver_ids.user_id, self.approver_1)

    def test_a_resync_deletes_and_recreates_in_the_right_order(self):
        cat_a = self._make_category(
            name="Resync From",
            approvers=[self.approver_1, self.approver_2],
        )
        cat_b = self._make_category(
            name="Resync To",
            approvers=[self.approver_2, self.manager_user],
        )
        request = self._prepare_request(cat_a, confirm=False)
        self.assertEqual(
            request.approver_ids.user_id,
            self.approver_1 | self.approver_2,
        )

        request.category_id = cat_b
        self.env.flush_all()

        self.assertEqual(
            request.approver_ids.user_id,
            self.approver_2 | self.manager_user,
            "The overlapping approver must survive and the orphan must go.",
        )
        self.assertEqual(
            len(request.approver_ids),
            2,
            "No duplicate row for the approver present in both categories.",
        )


@tagged("post_install", "-at_install")
class TestApproverSyncPlanLogging(ApprovalCommon):
    _LOGGER = "odoo.addons.approval.models.approval_request_routing"

    def _plan_steps(self, run):
        with self.assertLogs(self._LOGGER, level="DEBUG") as captured:
            run()
            self.env.flush_all()
        steps = []
        for line in captured.output:
            message = line.split(":", 2)[-1].strip()
            if not message.startswith("approver-sync  "):
                continue
            body = message.removeprefix("approver-sync").strip()
            if body[:1].isdigit():
                steps.append(body.split(".", 1)[1].strip())
        return steps

    def _executed_statements(self, run):
        verbs = []
        cursor_cls = type(self.env.cr)
        original_execute = cursor_cls.execute
        original_copy = cursor_cls.copy_from

        def execute(cr_self, query, params=None, log_exceptions=True):
            text = getattr(query, "code", None) or str(query)
            flat = " ".join(str(text).split()).upper()
            if re.search(r'"?APPROVAL_APPROVER"?(?![_A-Z])', flat):
                for verb in ("INSERT INTO", "DELETE FROM", "UPDATE"):
                    if verb in flat:
                        verbs.append(verb.split()[0].lower())
                        break
            if params is not None:
                return original_execute(cr_self, query, params, log_exceptions)
            return original_execute(cr_self, query)

        def copy_from(cr_self, table, columns, rows, **kwargs):
            if table == "approval_approver":
                verbs.append("create")
            return original_copy(cr_self, table, columns, rows, **kwargs)

        self.patch(cursor_cls, "execute", execute)
        self.patch(cursor_cls, "copy_from", copy_from)
        run()
        self.env.flush_all()
        return ["create" if v == "insert" else v for v in verbs]

    def test_a_batch_emits_one_create_step_for_all_requests(self):
        category = self._make_category(
            name="Plan Batch",
            approvers=[self.approver_1, self.approver_2],
        )

        steps = self._plan_steps(
            lambda: self.env["approval.request"].create(
                [
                    {
                        "category_id": category.id,
                        "request_owner_id": self.owner_user.id,
                    }
                    for _ in range(4)
                ],
            ),
        )

        create_steps = [s for s in steps if s.startswith("create")]
        self.assertEqual(
            len(create_steps),
            1,
            f"Four requests must plan ONE create step, got {steps}",
        )
        self.assertIn(
            "create 8 row(s)",
            create_steps[0],
            "The single create step must carry every row in the batch.",
        )

    def test_a_batch_issues_one_write_statement_for_all_rows(self):
        category = self._make_category(
            name="Plan Batch Cursor",
            approvers=[self.approver_1, self.approver_2],
        )

        verbs = self._executed_statements(
            lambda: self.env["approval.request"].create(
                [
                    {
                        "category_id": category.id,
                        "request_owner_id": self.owner_user.id,
                    }
                    for _ in range(4)
                ],
            ),
        )

        self.assertEqual(
            verbs.count("create"),
            1,
            f"Eight approver rows must be written by one statement; the "
            f"cursor saw {verbs}",
        )

    def test_deletes_execute_before_creates(self):
        source = self._make_category(
            name="Plan From",
            approvers=[self.approver_1, self.approver_2],
        )
        target = self._make_category(
            name="Plan To",
            approvers=[self.approver_2, self.manager_user],
        )
        request = self._prepare_request(source, confirm=False)
        self.env.flush_all()

        verbs = self._executed_statements(
            lambda: request.write({"category_id": target.id}),
        )

        self.assertIn("delete", verbs, f"Expected a delete; cursor saw {verbs}")
        self.assertIn("create", verbs, f"Expected a create; cursor saw {verbs}")
        self.assertLess(
            verbs.index("delete"),
            verbs.index("create"),
            f"Deletes must reach the database before creates; got {verbs}",
        )

    def test_the_log_faithfully_renders_the_executed_plan(self):
        source = self._make_category(
            name="Faithful From",
            approvers=[self.approver_1, self.approver_2],
        )
        target = self._make_category(
            name="Faithful To",
            approvers=[self.approver_2, self.manager_user],
        )
        request = self._prepare_request(source, confirm=False)
        self.env.flush_all()

        executed_plans = []
        request_cls = type(self.env["approval.request"])
        original = request_cls._execute_sync_plan

        def recording(model_self, plan):
            executed_plans.append([kind for kind, _payload in plan])
            return original(model_self, plan)

        self.patch(request_cls, "_execute_sync_plan", recording)

        logged = [
            step.split()[0]
            for step in self._plan_steps(
                lambda: request.write({"category_id": target.id}),
            )
        ]

        self.assertTrue(executed_plans, "No sync plan was executed at all.")
        self.assertEqual(
            logged,
            [kind for plan in executed_plans for kind in plan],
            "The DEBUG plan must list exactly the steps that were "
            "executed, in the same order.",
        )

    def test_updates_are_grouped_by_target_values(self):
        category = self._make_category(
            name="Plan Updates",
            approval_minimum=2,
            approvers=[
                (self.approver_1, False, 10),
                (self.approver_2, False, 10),
            ],
        )
        requests = self.env["approval.request"].create(
            [
                {"category_id": category.id, "request_owner_id": self.owner_user.id}
                for _ in range(3)
            ],
        )
        self.env.flush_all()
        category.step_ids.member_ids.write({"required": True, "sequence": 42})

        steps = self._plan_steps(requests._sync_approvers)

        update_steps = [s for s in steps if s.startswith("update")]
        self.assertEqual(
            len(update_steps),
            1,
            f"Six rows heading for identical values must plan ONE update "
            f"step, got {steps}",
        )
        self.assertIn("update 6 row(s)", update_steps[0])
        self.assertIn("sequence=42", update_steps[0])

    def test_a_no_op_resync_plans_nothing(self):
        category = self._make_category(name="Plan Noop", approvers=[self.approver_1])
        request = self._prepare_request(category, confirm=False)
        self.env.flush_all()

        steps = self._plan_steps(request._sync_approvers)

        self.assertEqual(
            steps,
            [],
            f"An unchanged draft must plan no row operations, got {steps}",
        )


@tagged("post_install", "-at_install")
class TestApproverSyncOnConfirm(ApprovalCommon):
    def test_confirm_picks_up_an_approver_added_after_the_draft(self):
        category = self._make_category(
            name="Confirm Resync Add",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category, confirm=False)
        self.assertEqual(request.approver_ids.user_id, self.approver_1)

        category.step_ids.minimum = 2
        category._add_approver(self.approver_2, required=True, sequence=20)

        request.action_confirm()

        self.assertEqual(
            request.approver_ids.user_id,
            self.approver_1 | self.approver_2,
            "The approver added to the category before confirmation must "
            "be part of the cycle the request confirms into.",
        )
        self.assertEqual(
            request.approval_minimum,
            2,
            "The effective minimum is re-derived from the category at "
            "confirmation, not frozen at creation.",
        )
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(
            request.state,
            "pending",
            "One approval can no longer carry the request: the second "
            "mandatory approver has to decide too.",
        )

    def test_confirm_drops_an_approver_removed_after_the_draft(self):
        category = self._make_category(
            name="Confirm Resync Remove",
            approval_minimum=2,
            approvers=[(self.approver_1, True, 10), (self.approver_2, True, 20)],
        )
        request = self._prepare_request(category, confirm=False)

        category.step_ids.member_ids.filtered(
            lambda member: member.user_id == self.approver_2,
        ).unlink()
        category.step_ids.minimum = 1

        request.action_confirm()

        self.assertEqual(
            request.approver_ids.user_id,
            self.approver_1,
            "A person the category no longer routes to must not be asked to approve.",
        )
        self.assertEqual(request.approval_minimum, 1)
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "approved")

    def test_confirm_snapshot_records_the_reconciled_set(self):
        category = self._make_category(
            name="Confirm Resync Snapshot",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category, confirm=False)
        category._add_approver(self.approver_2, sequence=20)

        request.action_confirm()

        snapshot_users = {
            entry["user_id"]
            for entry in request.category_snapshot["effective_approvers"]
        }
        self.assertEqual(
            snapshot_users,
            {self.approver_1.id, self.approver_2.id},
            "category_snapshot froze the pre-reconciliation set.",
        )

    def test_confirm_keeps_manual_approvers(self):
        category = self._make_category(
            name="Confirm Resync Manual",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
        )
        request = self._prepare_request(category, confirm=False)
        self.env["approval.approver"].create(
            {
                "request_id": request.id,
                "user_id": self.manager_user.id,
            },
        )

        request.action_confirm()

        self.assertIn(
            self.manager_user,
            request.approver_ids.user_id,
            "A manual approver must not be dropped by the confirm-time reconciliation.",
        )

    def test_confirm_of_an_untouched_draft_changes_nothing(self):
        category = self._make_category(
            name="Confirm Resync Noop",
            approval_minimum=2,
            approvers=[(self.approver_1, True, 10), (self.approver_2, True, 20)],
        )
        request = self._prepare_request(category, confirm=False)
        before = request.approver_ids.ids

        request.action_confirm()

        self.assertEqual(
            request.approver_ids.ids,
            before,
            "An unchanged category must not churn the approver rows at "
            "confirmation (their ids carry the To-Dos and the audit).",
        )


class TestManualRowsKeepWhatTheyWereGiven(ApprovalCommon):
    def test_resync_does_not_downgrade_a_manual_approver(self):
        category = self._make_category(name="Manual", approvers=[self.approver_1])
        request = self._prepare_request(category, confirm=False)
        manual = (
            self.env["approval.approver"]
            .with_user(self.manager_user)
            .create({"request_id": request.id, "user_id": self.approver_2.id})
        )
        manual.sudo().write({"required": True, "sequence": 5})

        request.with_user(self.owner_user).write({"priority": "2"})

        manual = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        self.assertTrue(manual.required)
        self.assertEqual(manual.sequence, 5)
        self.assertFalse(manual.source_synced)
