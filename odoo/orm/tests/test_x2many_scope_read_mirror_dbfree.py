from odoo import api, fields, models
from odoo.orm.domain import Domain
from odoo.orm.fields.relational._base import PENDING_SCOPE_KEY
from odoo.orm.model_test_env import model_test_env

_MOD = "test_x2many_scope_read_mirror"


class Order(models.Model):
    _name = "mirror.order"
    _module = _MOD
    _description = "an order whose total sums its lines under sudo"

    name = fields.Char()
    line_ids = fields.One2many("mirror.line", "order_id")
    held_ids = fields.One2many("mirror.line", "order_id", compute="_compute_held_ids")
    tag_ids = fields.Many2many("mirror.tag")
    total = fields.Integer(compute="_compute_total", store=True)

    @api.depends("line_ids.value")
    def _compute_total(self):
        for order in self:
            order.total = sum(order.line_ids.mapped("value"))

    @api.depends("line_ids")
    def _compute_held_ids(self):
        for order in self:
            order.held_ids = order.line_ids


class Line(models.Model):
    _name = "mirror.line"
    _module = _MOD
    _description = "a line"

    order_id = fields.Many2one("mirror.order")
    value = fields.Integer()
    secret = fields.Boolean()


class Tag(models.Model):
    _name = "mirror.tag"
    _module = _MOD
    _description = "a tag"

    name = fields.Char()


class IrModelAccess(models.AbstractModel):
    _name = "ir.model.access"
    _module = _MOD + "_access"
    _description = "ir.model.access (test stub)"

    def check(self, model, mode="read", raise_exception=True):
        return True


class IrRuleOpen(models.AbstractModel):
    _name = "ir.rule"
    _module = _MOD + "_rules_open"
    _description = "ir.rule (test stub, no rule narrows anything)"

    def _get_domain_accessible_records(self, model_name, mode="read"):
        return Domain.TRUE


class IrRuleOnLines(models.AbstractModel):
    _name = "ir.rule"
    _module = _MOD + "_rules_lines"
    _description = "ir.rule (test stub, secret lines are hidden from reads)"

    def _get_domain_accessible_records(self, model_name, mode="read"):
        if (model_name, mode) == ("mirror.line", "read"):
            return Domain("secret", "=", False)
        return Domain.TRUE


def _slots(env, field):
    return {
        key: dict(slot)
        for key, slot in env.core.iter_context_caches(field)
        if key != PENDING_SCOPE_KEY
    }


def _user_env(env):
    return env(user=2, su=False)


class TestCreatePrimesEveryScope:
    def test_a_created_record_holds_its_empty_x2many_for_the_superuser_too(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOpen) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            line_ids = order._fields["line_ids"]
            slots = _slots(env, line_ids)
            assert slots[as_user.env.get_cache_key(line_ids)] == {order.id: ()}
            assert slots[env.get_cache_key(line_ids)] == {order.id: ()}
            # the sudo compute read the empty value from the cache
            assert order.total == 0
            assert order.sudo().line_ids._ids == ()


class TestAUserReadFillsTheSuperuserSlot:
    def test_when_no_rule_narrows_the_comodel(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOpen) as env:
            order = env["mirror.order"].create({"name": "o"})
            lines = env["mirror.line"].create(
                [{"order_id": order.id, "value": 1}, {"order_id": order.id, "value": 2}]
            )
            env.invalidate_all()
            as_user = order.with_env(_user_env(env))
            assert as_user.line_ids._ids == lines._ids
            field = order._fields["line_ids"]
            assert _slots(env, field)[env.get_cache_key(field)] == {
                order.id: lines._ids
            }

    def test_a_many2many_read_fills_it_as_well(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOpen) as env:
            tags = env["mirror.tag"].create([{"name": "a"}, {"name": "b"}])
            order = env["mirror.order"].create({"name": "o", "tag_ids": tags.ids})
            env.invalidate_all()
            as_user = order.with_env(_user_env(env))
            assert as_user.tag_ids._ids == tags._ids
            field = order._fields["tag_ids"]
            assert _slots(env, field)[env.get_cache_key(field)] == {order.id: tags._ids}

    def test_not_when_a_rule_narrows_what_the_user_sees(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOnLines) as env:
            order = env["mirror.order"].create({"name": "o"})
            shown, hidden = env["mirror.line"].create(
                [
                    {"order_id": order.id, "value": 1},
                    {"order_id": order.id, "value": 2, "secret": True},
                ]
            )
            env.invalidate_all()
            as_user = order.with_env(_user_env(env))
            assert as_user.line_ids == shown.with_env(as_user.env)
            field = order._fields["line_ids"]
            assert env.get_cache_key(field) not in _slots(env, field)
            # the superuser's own read is not the user's filtered one
            assert order.sudo().line_ids._ids == (shown.id, hidden.id)

    def test_a_value_the_superuser_already_holds_is_kept(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOpen) as env:
            order = env["mirror.order"].create({"name": "o"})
            line = env["mirror.line"].create({"order_id": order.id, "value": 1})
            env.invalidate_all()
            field = order._fields["line_ids"]
            assert order.line_ids == line
            field._get_cache(env)[order.id] = ("planted",)
            as_user = order.with_env(_user_env(env))
            assert as_user.line_ids._ids == (line.id,)
            assert _slots(env, field)[env.get_cache_key(field)] == {
                order.id: ("planted",)
            }
            field._get_cache(env)[order.id] = (line.id,)


class TestTheWriterSlotListsWhatTheWriterMayRead:
    def test_a_line_the_creator_may_not_read_leaves_its_slot(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            shown = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 1})
            )
            field = order._fields["line_ids"]
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: (shown.id,)
            }
            hidden = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 2, "secret": True})
            )
            # the writer's slot is evicted: its next read searches and hides
            assert order.id not in _slots(env, field).get(
                as_user.env.get_cache_key(field), {}
            )
            assert order.line_ids == shown
            # the superuser's slot took both, as the superuser reads both
            assert order.sudo().line_ids._ids == (shown.id, hidden.id)
            assert order.sudo().total == 3

    def test_a_line_the_creator_may_read_stays_in_its_slot(self):
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create(
                {"name": "o", "line_ids": [(0, 0, {"value": 1}), (0, 0, {"value": 2})]}
            )
            field = order._fields["line_ids"]
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: order.line_ids._ids
            }
            assert len(order.line_ids) == 2

    def test_a_computed_inverse_has_one_slot_and_no_scope_to_evict(self):
        # a computed one2many naming the same inverse keeps one slot for every
        # scope (its access key is None): the writer's addition is not judged
        # against a reader, there is none to name
        with model_test_env(Order, Line, Tag, IrModelAccess, IrRuleOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            held = order._fields["held_ids"]
            assert as_user.env.get_cache_key(held) == (None,)
            assert not order.held_ids
            line = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 1, "secret": True})
            )
            assert order.sudo().held_ids == line.sudo()
