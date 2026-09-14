from datetime import date, timedelta

from odoo.fields import Command
from odoo.tests import common


def isolate_group_approval_manager(env, keep=None):
    keep = keep if keep is not None else env["res.users"]
    group = env.ref("approval.group_approval_manager")
    if "res.users.role" in env.registry:
        roles = env["res.users.role"].search([("implied_ids", "in", group.id)])
        if roles:
            for role in roles:
                role.implied_ids = [(3, group.id)]
            env["res.users.role"].search([]).update_users()

    company = env.company
    others = env["res.users"].search(
        [
            ("group_ids", "in", group.id),
            ("company_ids", "in", company.id),
            ("id", "not in", keep.ids),
        ],
    )
    if others:
        others.write({"group_ids": [(3, group.id)]})


# Shaped like the Business Trip data record, but owned by the test: demo data and
# users reconfigure that record's approvers, quorum and sequencing.
def new_trip_category(env, **values):
    return env["approval.category"].create(
        {
            "name": "Test Business Trip",
            "approval_minimum": 1,
            "privacy_visibility": "employees",
            **values,
        }
    )


def pool_step(members=(), minimum=1, **step_vals):
    return [
        Command.create(
            {
                "name": "In order" if step_vals.get("in_order") else "Approvers",
                "sequence": 10,
                "minimum": minimum,
                "counts_added_approvers": True,
                "member_ids": [
                    Command.create(
                        {"user_id": user_id, "required": required, "sequence": sequence}
                    )
                    for user_id, required, sequence in members
                ],
                **step_vals,
            }
        )
    ]


def add_rule_step(category, users, required=True, sequence=5, **rule_vals):
    rule = category.env["approval.rule"].create(
        {"category_id": category.id, "action_type": "condition", **rule_vals}
    )
    category.env["approval.category.step"].create(
        {
            "category_id": category.id,
            "name": rule.name,
            "sequence": 10,
            "minimum": 1,
            "advisory": not required,
            "when_rule_ids": [Command.set(rule.ids)],
            "member_ids": [
                Command.create(
                    {"user_id": user.id, "required": required, "sequence": sequence}
                )
                for user in users
            ],
        }
    )
    return rule


def add_category_approver(category, user, required=False, sequence=10):
    category._add_approver(user, required=required, sequence=sequence)


def record_approval(rows):
    rows.sudo()._record_decision("approved")


class ApprovalCommon(common.TransactionCase):
    _seq_code_counter = 0

    @classmethod
    def _next_sequence_code(cls):
        ApprovalCommon._seq_code_counter += 1
        return f"TC{ApprovalCommon._seq_code_counter:04d}"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner_user = cls.env["res.users"].create(
            {
                "name": "Request Owner",
                "login": "approval_common_owner",
                "email": "owner@test.com",
            },
        )
        cls.approver_1 = cls.env["res.users"].create(
            {
                "name": "Approver One",
                "login": "approval_common_approver_1",
                "email": "approver1.common@test.com",
                "group_ids": [
                    (4, cls.env.ref("approval.group_approval_approver").id),
                ],
            },
        )
        cls.approver_2 = cls.env["res.users"].create(
            {
                "name": "Approver Two",
                "login": "approval_common_approver_2",
                "email": "approver2.common@test.com",
                "group_ids": [
                    (4, cls.env.ref("approval.group_approval_approver").id),
                ],
            },
        )
        cls.manager_user = cls.env["res.users"].create(
            {
                "name": "Approval Manager",
                "login": "approval_common_manager",
                "email": "manager.common@test.com",
                "group_ids": [
                    (4, cls.env.ref("approval.group_approval_manager").id),
                ],
            },
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Approval Test Partner",
            },
        )

    @classmethod
    def _make_category(
        cls,
        name="Lifecycle Cat",
        code=None,
        approvers=None,
        in_order=False,
        group_id=False,
        asks_group_members=False,
        with_pool=None,
        **vals,
    ):
        code = code or cls._next_sequence_code()
        specs = [
            spec if isinstance(spec, tuple) else (spec, True, 10 * (index + 1))
            for index, spec in enumerate(approvers or ())
        ]
        required_count = sum(1 for _user, required, _sequence in specs if required)
        minimum = vals.pop("approval_minimum", max(1, required_count))
        if with_pool is None:
            with_pool = bool(specs or group_id or in_order)
        steps = (
            pool_step(
                [(user.id, required, sequence) for user, required, sequence in specs],
                minimum=minimum,
                in_order=in_order,
                group_id=group_id,
                asks_group_members=asks_group_members,
            )
            if with_pool
            else []
        )
        return cls.env["approval.category"].create(
            {
                "name": name,
                "sequence_code": code,
                "approval_minimum": minimum,
                "step_ids": steps,
                **vals,
            },
        )

    @classmethod
    def _prepare_request(cls, category, confirm=True, owner=None, **vals):
        request = cls.env["approval.request"].create(
            {
                "category_id": category.id,
                "request_owner_id": (owner or cls.owner_user).id,
                "reason": "<p>lifecycle test</p>",
                **vals,
            },
        )
        if confirm:
            request.action_confirm()
        return request

    def _delegate_row(self, row, delegate):
        today = date.today()
        row.sudo().write(
            {
                "delegate_id": delegate.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=1),
            },
        )
