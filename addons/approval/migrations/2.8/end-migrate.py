import logging

from odoo import SUPERUSER_ID, api
from odoo.fields import Command
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_ROUTING_ACTIONS = ("add_approver", "set_approvers")


def migrate(cr, version):
    if not _column_exists(cr, "approval_category", "group_approval"):
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    _refuse_routing_rules_on_lists(env)
    categories = _categories_on_their_list(env)
    for category, vals in _prepare_list_steps(cr, env, categories).items():
        category.write({"step_ids": [Command.create(vals)]})
        _logger.info(
            "approval category %s (#%s) now routes by its step '%s'",
            category.name,
            category.id,
            vals["name"],
        )
    cr.execute(
        SQL(
            "UPDATE approval_rule SET action_type = 'condition', active = FALSE "
            "WHERE action_type IN %s",
            _ROUTING_ACTIONS,
        )
    )
    if cr.rowcount:
        _logger.info(
            "approval: %s rule(s) that added or replaced approvers archived",
            cr.rowcount,
        )
    for request in _adopt_list_routed_requests(env):
        _logger.info(
            "approval request %s (#%s) now routes by the steps of %s, keeping its "
            "approvers and their decisions",
            request.name,
            request.id,
            request.category_id.name,
        )
    _log_census(env)


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        [table, column],
    )
    return bool(cr.fetchone())


def _module_categories(env):
    eco = env.ref("mrp_plm.approval_category_eco", raise_if_not_found=False)
    return eco or env["approval.category"]


def _refuse_routing_rules_on_lists(env):
    env.cr.execute(
        """
        SELECT rule.category_id, rule.name
          FROM approval_rule rule
          JOIN approval_category category ON category.id = rule.category_id
         WHERE rule.active
           AND NOT EXISTS (
               SELECT 1 FROM approval_category_step step
                WHERE step.category_id = category.id
           )
           AND (
               rule.action_type = 'add_approver'
               OR (rule.action_type = 'set_approvers'
                   AND category.group_approval != 'exclusive')
           )
         ORDER BY rule.category_id, rule.id
        """
    )
    blocked = env.cr.fetchall()
    if blocked:
        categories = env["approval.category"].browse({row[0] for row in blocked})
        names = {category.id: category.display_name for category in categories}
        raise RuntimeError(
            "approval 2.8 routes every request by steps and no longer converts a rule "
            "that adds or replaces approvers. Before upgrading, remove these rules: "
            + "; ".join(
                f"{names[category_id]} (#{category_id}): {rule}"
                for category_id, rule in blocked
            )
        )


def _categories_on_their_list(env):
    categories = env["approval.category"].search([("step_ids", "=", False)])
    return categories - _module_categories(env)


def _prepare_list_steps(cr, env, categories):
    if not categories:
        return {}
    cr.execute(
        """
        SELECT id, approval_minimum, approve_sequentially, group_approval,
               approver_group_id, notify_pool_members
          FROM approval_category
         WHERE id = ANY(%s)
        """,
        [categories.ids],
    )
    settings = {row[0]: row[1:] for row in cr.fetchall()}
    cr.execute(
        """
        SELECT category_id, user_id, required, sequence
          FROM approval_category_approver
         WHERE category_id = ANY(%s)
         ORDER BY category_id, sequence, id
        """,
        [categories.ids],
    )
    listed = {}
    for category_id, user_id, required, sequence in cr.fetchall():
        listed.setdefault(category_id, []).append((user_id, required, sequence))
    prepared = {}
    for category in categories:
        minimum, sequential, group_approval, group_id, asks_members = settings[
            category.id
        ]
        by_group = group_approval == "exclusive" and group_id
        members = [] if by_group else listed.get(category.id, [])
        in_order = bool(sequential) and not by_group
        prepared[category] = {
            "name": env._("In order") if in_order else env._("Approvers"),
            "sequence": 10,
            "minimum": max(minimum or 1, 1),
            "counts_added_approvers": True,
            "in_order": in_order,
            "member_ids": [
                Command.create(
                    {"user_id": user_id, "required": required, "sequence": sequence}
                )
                for user_id, required, sequence in members
            ],
            **(
                {"group_id": group_id, "asks_group_members": bool(asks_members)}
                if by_group
                else {}
            ),
        }
    return prepared


def _adopt_list_routed_requests(env):
    pending = env["approval.request"].search(
        [("state", "=", "pending"), ("category_id.step_ids", "!=", False)]
    )
    adopted = env["approval.request"]
    for request in pending.filtered(lambda request: not request.approver_ids.step_ids):
        desired = request._get_desired_approvers()
        for row in request.approver_ids:
            vals = desired.staging.get(row.user_id.id)
            if vals is None:
                continue
            row_vals = {
                "step_ids": [Command.set(vals["step_ids"])],
                "required": vals["required"],
                "sequence": vals["sequence"],
                "source_synced": vals.get("source_synced", True),
            }
            if row.state == "approved":
                row_vals["decided_step_ids"] = [Command.set(vals["step_ids"])]
            if row.state == "waiting":
                row_vals["flow_state"] = "pending"
            row.write(row_vals)
        created = request._create_live_approver_rows(desired.to_create)
        for row in created:
            row.write(
                {
                    "step_ids": [
                        Command.set(desired.to_create[row.user_id.id]["step_ids"])
                    ]
                }
            )
        request.approval_minimum = sum(
            request._get_applicable_steps().mapped("minimum")
        )
        request.invalidate_recordset()
        request.approver_ids.filtered(
            lambda row: row.state == "pending"
        )._create_activity()
        request._refresh_turn_states()
        request._retire_unasked_approval_activities()
        adopted |= request
    return adopted


def _log_census(env):
    categories = env["approval.category"].search([("step_ids", "=", False)])
    categories -= _module_categories(env)
    undecided = env["approval.request"].search([("state", "in", ("new", "pending"))])
    requests = undecided.filtered(
        lambda request: (
            request.category_id in categories
            or (request.state == "pending" and not request.approver_ids.step_ids)
        )
    )
    _logger.info(
        "approval: %s undecided request(s) still route by an approver list, "
        "%s categor(ies) still do",
        len(requests),
        len(categories),
    )
