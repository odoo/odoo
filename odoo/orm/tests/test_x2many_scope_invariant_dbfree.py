"""The x2many scope invariant, under random walks.

doc/architecture/runtime.md states it: a scope's slot for a stored x2many
either holds exactly what that scope's search would return now, or holds
nothing. The maintenance rules (read fills, full write evicts the others,
inverse-side addition appends to the superuser and the writer and evicts the
rest, removal applies everywhere) are each pinned by a named test elsewhere;
this file checks the invariant they exist for, after every step of a random
sequence of reads and writes by users in several company scopes and the
superuser, over a plain one2many, one with a callable domain, one that
bypasses search access, and a many2many.

The one stated exception -- the writer's own slot lists what the writer wrote
even when its read rule hides it -- is kept out of the walk by construction: a
user never writes `secret`, so what a user writes is what the user reads.
"""

import random

import pytest

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.orm.domain import Domain
from odoo.orm.fields.relational._base import PENDING_SCOPE_KEY
from odoo.orm.model_test_env import model_test_env
from odoo.orm.primitives import Command

_MOD = "test_x2many_scope_invariant"


class Order(models.Model):
    _name = "inv.order"
    _module = _MOD
    _description = "an order"

    name = fields.Char()
    line_ids = fields.One2many("inv.line", "order_id")
    positive_line_ids = fields.One2many(
        "inv.line", "order_id", domain=lambda self: [("value", ">", 0)]
    )
    any_line_ids = fields.One2many("inv.line", "order_id", bypass_search_access=True)
    tag_ids = fields.Many2many("inv.tag")
    total = fields.Integer(compute="_compute_total", store=True)

    @api.depends("line_ids.value")
    def _compute_total(self):
        for order in self:
            order.total = sum(order.line_ids.mapped("value"))


class Line(models.Model):
    _name = "inv.line"
    _module = _MOD
    _description = "a line"
    _order = "value, id"

    order_id = fields.Many2one("inv.order")
    value = fields.Integer()
    secret = fields.Boolean()
    company_id = fields.Many2one("res.company")


class Tag(models.Model):
    _name = "inv.tag"
    _module = _MOD
    _description = "a tag"
    _order = "name, id"

    name = fields.Char()
    secret = fields.Boolean()
    order_ids = fields.Many2many(
        "inv.order", "inv_order_inv_tag_rel", "inv_tag_id", "inv_order_id"
    )


class IrModelAccess(models.AbstractModel):
    _name = "ir.model.access"
    _module = _MOD + "_access"
    _description = "ir.model.access (test stub)"

    def check(self, model, mode="read", raise_exception=True):
        return True


class IrRule(models.AbstractModel):
    _name = "ir.rule"
    _module = _MOD + "_rules"
    _description = (
        "ir.rule (test stub): secret lines and tags are hidden from user reads, "
        "a line of another company too"
    )

    def _get_domain_accessible_records(self, model_name, mode="read"):
        if mode != "read":
            return Domain.TRUE
        if model_name == "inv.tag":
            return Domain("secret", "=", False)
        if model_name == "inv.line":
            return Domain("secret", "=", False) & (
                Domain("company_id", "=", False)
                | Domain("company_id", "in", self.env.companies.ids)
            )
        return Domain.TRUE

    def _prepare_access_error(self, operation, records):
        return AccessError(f"{operation} denied on {records}")


# "two" belongs to both companies, "three" to the second; a scope is a user
# with the companies it has switched to
SCOPES = (
    ("two@c1", "two", ("c1",)),
    ("two@c1c2", "two", ("c1", "c2")),
    ("three@c2", "three", ("c2",)),
)
STORED_X2MANY = ("line_ids", "positive_line_ids", "any_line_ids", "tag_ids")


def _scopes(env, users, companies):
    scopes = {"sudo": env}
    for name, user, company_names in SCOPES:
        scopes[name] = env(
            user=users[user].id,
            context={"allowed_company_ids": [companies[c].id for c in company_names]},
            su=False,
        )
    return scopes


def _truth(scope_env, field, record_id):
    # what the scope's search returns: the field's domain over the relation,
    # then the scope's read rule; bypass_search_access relaxes a search
    # *through* the field, never the field's own read. Neither comodel
    # overrides _search
    comodel = scope_env[field.comodel_name].sudo()
    host = scope_env[field.model_name].browse(record_id)
    if field.is_one2many:
        domain = Domain(field.inverse_name, "=", record_id)
    else:
        domain = Domain("order_ids", "in", [record_id])
    domain &= field.get_comodel_domain(host)
    related = comodel.browse(
        comodel._search(domain, order=comodel._order, active_test=False)
    )
    if not scope_env.su:
        rule = scope_env.registry.access_policy.record_domain(
            scope_env, field.comodel_name, "read"
        )
        related = related.filtered_domain(rule)
    return related._ids


def _check_invariant(env, scopes, orders, log):
    env.flush_all()
    for field in (orders._fields[name] for name in STORED_X2MANY):
        for key, slot in list(env.core.iter_context_caches(field)):
            if key == PENDING_SCOPE_KEY:
                continue
            for name, scope_env in scopes.items():
                if scope_env.get_cache_key(field) != key:
                    continue
                for order_id in orders._ids:
                    if order_id not in slot:
                        continue
                    held = slot[order_id]
                    truth = _truth(scope_env, field, order_id)
                    why = (
                        f"{name}'s slot of {field} for order {order_id} holds {held}, "
                        f"its search returns {truth}; after:\n  " + "\n  ".join(log)
                    )
                    assert set(held) == set(truth), why
                    # the order is the search's whenever the sort keys are in
                    # memory; a write whose keys are not caches the written order
                    comodel = env[field.comodel_name]
                    if (
                        comodel.browse(held)._sorted_by_ids(comodel._order, False)
                        is not None
                    ):
                        assert held == truth, why


def _walk(seed, steps):
    rng = random.Random(seed)
    log = []
    with model_test_env(Order, Line, Tag, IrModelAccess, IrRule) as env:
        c1, c2 = env["res.company"].create([{"name": "c1"}, {"name": "c2"}])
        companies = {"c1": c1, "c2": c2}
        two, three = env["res.users"].create(
            [
                {
                    "name": "two",
                    "company_id": c1.id,
                    "company_ids": [Command.link(c2.id)],
                },
                {"name": "three", "company_id": c2.id},
            ]
        )
        scopes = _scopes(env, {"two": two, "three": three}, companies)
        company_ids = [False, c1.id, c2.id]
        orders = env["inv.order"].create([{"name": f"o{i}"} for i in range(3)])
        tags = env["inv.tag"].create(
            [{"name": f"t{i}", "secret": i == 3} for i in range(4)]
        )
        env["inv.line"].create(
            [
                {"order_id": order.id, "value": i, "secret": i == 0}
                for i, order in enumerate(orders)
            ]
        )
        env.invalidate_all()

        for step in range(steps):
            name, scope_env = rng.choice(list(scopes.items()))
            order = orders[rng.randrange(len(orders))].with_env(scope_env)
            op = rng.choice(
                [
                    "read_lines",
                    "read_tags",
                    "create_line",
                    "move_line",
                    "unlink_line",
                    "set_lines",
                    "link_tag",
                    "unlink_tag",
                    "set_tags",
                    "invalidate",
                    "read_total",
                    "toggle_secret",
                    "read_positive",
                    "read_any",
                    "move_company",
                ]
            )
            log.append(f"{step}: {name} {op} on {order.name}")
            # the walk keeps the sort keys in memory, so the invariant's order
            # clause is what it tests; a write whose keys are not cached keeps
            # the written order, pinned by name in test_x2many_scope_read_mirror
            env["inv.line"].search([]).mapped("value")
            tags.mapped("name")
            try:
                _apply(op, name, scope_env, order, orders, tags, rng, env, company_ids)
            except AccessError as exc:
                # a denied write changes nothing, and the slots must say so
                log[-1] += f" (denied: {exc})"
            _check_invariant(env, scopes, orders, log)


def _apply(op, name, scope_env, order, orders, tags, rng, env, company_ids):
    def lines_of(order):
        return scope_env["inv.line"].search([("order_id", "=", order.id)])

    match op:
        case "read_lines":
            _ = order.line_ids
        case "read_tags":
            _ = order.tag_ids
        case "read_total":
            _ = order.total
        case "create_line":
            secret = name == "sudo" and rng.random() < 0.3
            companies = (
                company_ids if name == "sudo" else [False, *scope_env.companies.ids]
            )
            scope_env["inv.line"].create(
                {
                    "order_id": order.id,
                    "value": rng.randrange(-2, 10),
                    "secret": secret,
                    "company_id": rng.choice(companies),
                }
            )
        case "move_line":
            if line := lines_of(order)[:1]:
                line.write({"order_id": orders[rng.randrange(len(orders))].id})
        case "unlink_line":
            if line := lines_of(order)[:1]:
                line.unlink()
        case "set_lines":
            keep = lines_of(order).filtered(lambda _l: rng.random() < 0.5)
            order.write({"line_ids": [Command.set(keep.ids)]})
        case "link_tag" | "unlink_tag":
            tag = tags[rng.randrange(len(tags))]
            if name == "sudo" or not tag.secret:
                command = Command.link if op == "link_tag" else Command.unlink
                order.write({"tag_ids": [command(tag.id)]})
        case "set_tags":
            pool = tags if name == "sudo" else tags.filtered(lambda t: not t.secret)
            chosen = pool.filtered(lambda _t: rng.random() < 0.5)
            order.write({"tag_ids": [Command.set(chosen.ids)]})
        case "toggle_secret":
            if name == "sudo":
                if line := lines_of(order)[:1]:
                    line.write({"secret": not line.secret})
        case "read_positive":
            _ = order.positive_line_ids
        case "read_any":
            _ = order.any_line_ids
        case "move_company":
            # a user may move a line it reads to a company it belongs to
            if line := lines_of(order)[:1]:
                choices = (
                    company_ids if name == "sudo" else [False, *scope_env.companies.ids]
                )
                line.write({"company_id": rng.choice(choices)})
        case "invalidate":
            env.invalidate_all()


@pytest.mark.parametrize("seed", range(40))
def test_every_scope_slot_equals_its_search_or_is_absent(seed):
    _walk(seed, steps=60)
