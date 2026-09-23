from odoo import api, fields, models
from odoo.orm.domain import Domain
from odoo.orm.fields.relational._base import PENDING_SCOPE_KEY
from odoo.orm.model_test_env import model_test_env
from odoo.orm.primitives import Command

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

    sudo_assigned_ids = fields.Many2many(
        "mirror.line", compute="_compute_sudo_assigned_ids"
    )
    unassigned_ids = fields.Many2many(
        "mirror.line", compute="_compute_unassigned_ids", readonly=False
    )

    @api.depends("line_ids")
    def _compute_sudo_assigned_ids(self):
        for order in self:
            order.sudo().sudo_assigned_ids = order.line_ids

    def _compute_unassigned_ids(self):
        return


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
    _order = "name, id"

    name = fields.Char()


class IrAccessOpen(models.AbstractModel):
    _name = "ir.access"
    _module = _MOD + "_access_open"
    _description = "ir.access (test stub, no row narrows anything)"

    def _policy_signature(self):
        return (self.env.uid, *self._get_access_context())

    def _get_access_context(self):
        company_ids = self.env.context.get("allowed_company_ids")
        yield tuple(company_ids) if company_ids else company_ids

    def _bound_access_rows(self, model_name, operation):
        return [Domain.TRUE], []


class IrAccessOnLines(models.AbstractModel):
    _name = "ir.access"
    _module = _MOD + "_access_lines"
    _description = "ir.access (test stub, secret lines are hidden from reads)"

    def _policy_signature(self):
        return (self.env.uid, *self._get_access_context())

    def _get_access_context(self):
        company_ids = self.env.context.get("allowed_company_ids")
        yield tuple(company_ids) if company_ids else company_ids

    def _bound_access_rows(self, model_name, operation):
        if (model_name, operation) == ("mirror.line", "read"):
            return [Domain("secret", "=", False)], []
        return [Domain.TRUE], []


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
        with model_test_env(Order, Line, Tag, IrAccessOpen) as env:
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
        with model_test_env(Order, Line, Tag, IrAccessOpen) as env:
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
        with model_test_env(Order, Line, Tag, IrAccessOpen) as env:
            tags = env["mirror.tag"].create([{"name": "a"}, {"name": "b"}])
            order = env["mirror.order"].create({"name": "o", "tag_ids": tags.ids})
            env.invalidate_all()
            as_user = order.with_env(_user_env(env))
            assert as_user.tag_ids._ids == tags._ids
            field = order._fields["tag_ids"]
            assert _slots(env, field)[env.get_cache_key(field)] == {order.id: tags._ids}

    def test_not_when_a_rule_narrows_what_the_user_sees(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
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
        with model_test_env(Order, Line, Tag, IrAccessOpen) as env:
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


class TestTheWriterSlotListsWhatTheWriterWrote:
    def test_a_line_the_creator_may_not_read_stays_in_its_slot_until_a_search(self):
        # the writer's slot appends what the writer wrote, judged by nobody:
        # judging would cost the comodel's read check on every write, and the
        # writer's own write is visible to the writer inside its transaction
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            shown = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 1})
            )
            hidden = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 2, "secret": True})
            )
            field = order._fields["line_ids"]
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: (shown.id, hidden.id)
            }
            assert order.sudo().line_ids._ids == (shown.id, hidden.id)
            assert order.sudo().total == 3
            order.invalidate_recordset(["line_ids"])
            assert order.line_ids == shown

    def test_a_line_the_creator_may_read_stays_in_its_slot(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create(
                {"name": "o", "line_ids": [(0, 0, {"value": 1}), (0, 0, {"value": 2})]}
            )
            field = order._fields["line_ids"]
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: order.line_ids._ids
            }
            assert len(order.line_ids) == 2

    def test_a_computed_inverse_is_scoped_by_its_reader_and_recomputes_for_sudo(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            held = order._fields["held_ids"]
            assert as_user.env.get_cache_key(held) == ((2, (1,)),)
            assert not order.held_ids
            line = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 1, "secret": True})
            )
            assert order.sudo().held_ids == line.sudo()


def _count_access_filters(monkeypatch):
    from odoo.orm.models import BaseModel

    calls = []
    original = BaseModel._filtered_access

    def counted(self, operation):
        calls.append((self._name, operation))
        return original(self, operation)

    monkeypatch.setattr(BaseModel, "_filtered_access", counted)
    return calls


class TestABatchJudgesNoScope:
    def test_a_superuser_batch_over_many_hosts_evicts_the_user_scope(self, monkeypatch):
        # _message_log_batch: N messages on N threads, created under sudo,
        # while the user's slot holds every thread's x2many
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            orders = as_user.create([{"name": f"o{i}"} for i in range(10)])
            calls = _count_access_filters(monkeypatch)
            lines = env["mirror.line"].create(
                [
                    {"order_id": order.id, "value": i, "secret": i == 3}
                    for i, order in enumerate(orders)
                ]
            )
            assert calls == []
            field = orders._fields["line_ids"]
            slots = _slots(env, field)
            assert slots[as_user.env.get_cache_key(field)] == {}
            assert slots[env.get_cache_key(field)] == {
                order.id: (line.id,) for order, line in zip(orders, lines, strict=True)
            }
            # the user's next read searches, and the search hides the secret
            assert orders[3].with_env(as_user.env).line_ids._ids == ()
            assert orders[0].with_env(as_user.env).line_ids == lines[0]

    def test_a_user_batch_over_many_hosts_appends_to_its_own_scope(self, monkeypatch):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            orders = as_user.create([{"name": f"o{i}"} for i in range(10)])
            calls = _count_access_filters(monkeypatch)
            lines = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create(
                    [
                        {"order_id": order.id, "value": i, "secret": i == 3}
                        for i, order in enumerate(orders)
                    ]
                )
            )
            assert calls == []
            field = orders._fields["line_ids"]
            slots = _slots(env, field)
            expected = {
                order.id: (line.id,) for order, line in zip(orders, lines, strict=True)
            }
            assert slots[as_user.env.get_cache_key(field)] == expected
            assert slots[env.get_cache_key(field)] == expected
            assert orders.sudo()[3].line_ids == lines[3].sudo()


class TestAWriteToARuleFieldEvictsTheScopesThatReadThroughIt:
    def test_hiding_a_line_evicts_the_user_slot_and_keeps_the_superuser_slot(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            line = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 1})
            )
            field = order._fields["line_ids"]
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: (line.id,)
            }
            line.sudo().write({"secret": True})
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {}
            assert _slots(env, field)[env.get_cache_key(field)] == {
                order.id: (line.id,)
            }
            assert order.line_ids._ids == ()
            line.sudo().write({"secret": False})
            assert order.line_ids == line

    def test_a_write_to_a_field_no_rule_tests_keeps_every_slot(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            as_user = _user_env(env)["mirror.order"]
            order = as_user.create({"name": "o"})
            line = (
                env["mirror.line"]
                .with_env(as_user.env)
                .create({"order_id": order.id, "value": 1})
            )
            field = order._fields["line_ids"]
            line.sudo().write({"value": 2})
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: (line.id,)
            }


class TestAStoredMany2manyWriteCachesTheComodelOrder:
    def test_with_the_sort_keys_in_memory_the_slot_reads_as_a_fetch_would(self):
        with model_test_env(Order, Line, Tag, IrAccessOpen) as env:
            b, a = env["mirror.tag"].create([{"name": "b"}, {"name": "a"}])
            order = env["mirror.order"].create({"name": "o"})
            order.write({"tag_ids": [Command.set([b.id, a.id])]})
            assert order.tag_ids._ids == (a.id, b.id)

    def test_without_the_sort_keys_the_slot_keeps_the_written_order(self):
        with model_test_env(Order, Line, Tag, IrAccessOpen) as env:
            b, a = env["mirror.tag"].create([{"name": "b"}, {"name": "a"}])
            order = env["mirror.order"].create({"name": "o"})
            env.flush_all()
            env.invalidate_all()
            # no fetch inside a write: the names are not read to sort
            order.write({"tag_ids": [Command.set([b.id, a.id])]})
            field = order._fields["tag_ids"]
            assert field._get_cache(env)[order.id] == (b.id, a.id)
            order.invalidate_recordset(["tag_ids"])
            assert order.tag_ids._ids == (a.id, b.id)


class TestAComputeAssigningThroughSudoAnswersItsReader:
    # account.move.line.reconciled_lines_ids: the compute runs as the reader and
    # writes `line.sudo().field = value`, which lands in the superuser slot

    def test_the_reader_slot_takes_what_its_own_compute_assigned_under_sudo(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            order = env["mirror.order"].create({"name": "o"})
            shown, _hidden = env["mirror.line"].create(
                [
                    {"order_id": order.id, "value": 1},
                    {"order_id": order.id, "value": 2, "secret": True},
                ]
            )
            env.invalidate_all()
            as_user = order.with_env(_user_env(env))
            field = order._fields["sudo_assigned_ids"]

            assert as_user.sudo_assigned_ids._ids == (shown.id,)
            assert _slots(env, field)[as_user.env.get_cache_key(field)] == {
                order.id: (shown.id,)
            }

    def test_a_value_the_superuser_slot_held_before_is_not_adopted(self):
        with model_test_env(Order, Line, Tag, IrAccessOnLines) as env:
            order = env["mirror.order"].create({"name": "o"})
            hidden = env["mirror.line"].create(
                {"order_id": order.id, "value": 2, "secret": True}
            )
            order.unassigned_ids = hidden
            as_user = order.with_env(_user_env(env))

            assert not as_user.unassigned_ids
