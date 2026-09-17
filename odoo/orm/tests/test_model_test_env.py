import pytest

from odoo import Command, api, fields, models
from odoo.orm.model_test_env import (
    InMemorySqlNotSupported,
    ModelRegistry,
    model_test_env,
)

_MOD = "test_orm_harness"


class HWidget(models.Model):
    _name = "h.widget"
    _module = _MOD
    _description = "Harness Widget"

    name = fields.Char()
    price = fields.Float()
    qty = fields.Integer()
    total = fields.Float(compute="_compute_total", store=True)
    discounted = fields.Float(compute="_compute_discounted", store=True)

    @api.depends("price", "qty")
    def _compute_total(self):
        for rec in self:
            rec.total = rec.price * rec.qty

    @api.depends("total")
    def _compute_discounted(self):
        for rec in self:
            rec.discounted = rec.total * 0.9


class HAnimal(models.Model):
    _name = "h.animal"
    _module = _MOD
    _description = "Harness Animal"

    name = fields.Char()
    sound = fields.Char()


class HAnimalLegs(models.Model):
    _inherit = "h.animal"
    _module = _MOD

    legs = fields.Integer(default=4)

    def describe(self):
        self.check_singleton()
        return f"{self['name']} says {self['sound']} on {self.legs} legs"


class HEngine(models.Model):
    _name = "h.engine"
    _module = _MOD
    _description = "Harness Engine"

    power = fields.Integer()


class HCar(models.Model):
    _name = "h.car"
    _module = _MOD
    _description = "Harness Car"
    _inherits = {"h.engine": "engine_id"}

    engine_id = fields.Many2one("h.engine", required=True, ondelete="cascade")
    brand = fields.Char()


class HOrder(models.Model):
    _name = "h.order"
    _module = _MOD
    _description = "Harness Order"

    name = fields.Char()
    line_ids = fields.One2many("h.line", "order_id")
    amount = fields.Float(compute="_compute_amount", store=True)

    @api.depends("line_ids.subtotal")
    def _compute_amount(self):
        for order in self:
            order.amount = sum(order.line_ids.mapped("subtotal"))


class HLine(models.Model):
    _name = "h.line"
    _module = _MOD
    _description = "Harness Order Line"

    order_id = fields.Many2one("h.order", ondelete="cascade")
    price = fields.Float()
    qty = fields.Integer()
    subtotal = fields.Float(compute="_compute_subtotal", store=True)

    @api.depends("price", "qty")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.price * line.qty


class HTag(models.Model):
    _name = "h.tag"
    _module = _MOD
    _description = "Harness Tag"
    _log_access = False

    name = fields.Char()
    active = fields.Boolean(default=True)
    post_ids = fields.Many2many("h.post")


class HPost(models.Model):
    _name = "h.post"
    _module = _MOD
    _description = "Harness Post"
    _log_access = False

    name = fields.Char()
    tag_ids = fields.Many2many("h.tag")


class HBook(models.Model):
    _name = "h.book"
    _module = _MOD
    _description = "Harness Book"
    _log_access = False

    title = fields.Char(translate=True)


def test_create_persists_and_reads_back():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        b = env["h.widget"].create({"name": "B", "price": 5.0, "qty": 10})
        assert a.id == 1 and b.id == 2
        assert a.name == "A" and a.price == 10.0 and a.qty == 3


def test_write_updates_field():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        a.qty = 4
        assert a.qty == 4


def test_stored_compute_cascades_on_create():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        b = env["h.widget"].create({"name": "B", "price": 5.0, "qty": 10})
        assert a.total == 30.0 and b.total == 50.0


def test_stored_compute_recomputes_on_write():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        assert a.total == 30.0
        a.qty = 5
        assert a.total == 50.0


def test_transitive_compute_cascade():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        assert a.total == 30.0
        assert abs(a.discounted - 27.0) < 1e-9
        a.price = 20.0
        assert a.total == 60.0
        assert abs(a.discounted - 54.0) < 1e-9


def test_explicit_compute_still_works():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        a._compute_total()
        assert a.total == 30.0


def test_relational_cascade_through_one2many():
    with model_test_env(HOrder) as env:
        order = env["h.order"].create({"name": "O1"})
        env["h.line"].create({"order_id": order.id, "price": 10.0, "qty": 2})
        line2 = env["h.line"].create({"order_id": order.id, "price": 5.0, "qty": 3})
        assert order.amount == 35.0
        line2.qty = 5
        assert order.amount == 45.0


def test_new_record_lazy_compute():
    with model_test_env(HWidget) as env:
        n = env["h.widget"].new({"price": 2.0, "qty": 5})
        assert n.total == 10.0


def test_filtered_mapped_sorted():
    with model_test_env(HWidget) as env:
        a = env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        b = env["h.widget"].create({"name": "B", "price": 5.0, "qty": 10})
        (a + b)._compute_total()
        both = a + b
        assert both.filtered(lambda r: r.total > 45).mapped("name") == ["B"]
        assert both.sorted("total").mapped("name") == ["A", "B"]


def test_search_via_in_memory_backend():
    with model_test_env(HWidget) as env:
        env["h.widget"].create({"name": "A", "price": 10.0, "qty": 3})
        env["h.widget"].create({"name": "B", "price": 5.0, "qty": 10})
        found = env["h.widget"].search([("price", ">", 7.0)])
        assert found.mapped("name") == ["A"]


def test_filtered_id_keeps_only_saved_records():
    with model_test_env(HWidget) as env:
        saved = env["h.widget"].create([{"name": "A"}, {"name": "B"}])
        draft = env["h.widget"].new({"name": "draft"})
        kept = (saved + draft).filtered("id")
        assert kept._ids == saved._ids


def test_write_multi_aliased_vals_not_uniform():
    # _write_multi bypasses the cache on purpose: no cache-against-rows check
    with model_test_env(HWidget, check_cache=False) as env:
        recs = env["h.widget"].create([{"qty": 1}, {"qty": 2}, {"qty": 3}])
        a, b = {"qty": 100}, {"qty": 200}
        recs._write_multi([a, b, a])
        table = env["h.widget"]._table
        persisted = [env.cr.storage.get_row(table, i)["qty"] for i in recs._ids]
        assert persisted == [100, 200, 100]


def test_ir_default_is_injected():
    with model_test_env(HWidget) as env:
        assert "ir.default" in env.registry
        assert env["ir.default"]._get_model_defaults("h.widget") == {}
        rec = env["h.widget"].create({})
        assert rec.id


def test_inherit_extension_adds_field_and_method():
    with model_test_env(HAnimal) as env:
        cat = env["h.animal"].create({"name": "Cat", "sound": "meow"})
        assert cat.legs == 4
        cat.legs = 3
        assert cat.describe() == "Cat says meow on 3 legs"


def test_inherits_delegation_exposes_parent_fields():
    with model_test_env(HCar) as env:
        engine = env["h.engine"].create({"power": 100})
        car = env["h.car"].create({"brand": "Acme", "engine_id": engine.id})
        assert car.power == 100
        assert car.brand == "Acme"


def test_raw_sql_fails_loud_instead_of_returning_empty():
    with model_test_env(HWidget) as env:
        env["h.widget"].create({"name": "A", "price": 10.0, "qty": 1})
        with pytest.raises(InMemorySqlNotSupported):
            env.cr.execute("SELECT count(*) FROM h_widget")
        # read_group answers in memory now; a grouped read is no longer raw SQL
        assert env["h.widget"]._read_group([], ["name"], ["__count"]) == [("A", 1)]


def test_fixtures_opt_in_for_raw_sql():
    with model_test_env(HWidget, fixtures={"SELECT 1": [(42,)]}) as env:
        env.cr.execute("SELECT 1")
        assert env.cr.fetchall() == [(42,)]
        with pytest.raises(InMemorySqlNotSupported):
            env.cr.execute("SELECT 2")


def test_dict_cursor_api_fails_loud_for_tuple_fixture():
    with model_test_env(HWidget, fixtures={"SELECT 1": [(42,)], "SELECT 0": []}) as env:
        env.cr.execute("SELECT 1")
        assert env.cr.fetchall() == [(42,)]
        assert env.cr.fetchone() == (42,)
        with pytest.raises(InMemorySqlNotSupported):
            env.cr.dictfetchall()
        with pytest.raises(InMemorySqlNotSupported):
            env.cr.dictfetchone()
        env.cr.execute("SELECT 0")
        assert env.cr.dictfetchall() == []
        assert env.cr.dictfetchone() is None


def _fresh(env, records):
    env.flush_all()
    env.invalidate_all()
    return records


def test_m2m_model_set_builds():
    with model_test_env(HPost) as env:
        assert "h.post" in env.registry and "h.tag" in env.registry
        key = next(iter(env.registry.many2many_relations))
        assert key[0] == "h_post_h_tag_rel"


def test_m2m_create_set_roundtrips_through_backend():
    with model_test_env(HPost) as env:
        t1 = env["h.tag"].create({"name": "t1"})
        t2 = env["h.tag"].create({"name": "t2"})
        post = env["h.post"].create(
            {"name": "p", "tag_ids": [Command.set([t1.id, t2.id])]}
        )
        _fresh(env, post)
        assert post.tag_ids._ids == (t1.id, t2.id)
        assert t1.post_ids._ids == (post.id,)


def test_m2m_link_unlink_commands():
    with model_test_env(HPost) as env:
        t1 = env["h.tag"].create({"name": "t1"})
        t2 = env["h.tag"].create({"name": "t2"})
        post = env["h.post"].create({"name": "p"})
        post.write({"tag_ids": [Command.link(t1.id), Command.link(t2.id)]})
        _fresh(env, post)
        assert post.tag_ids._ids == (t1.id, t2.id)
        post.write({"tag_ids": [Command.unlink(t1.id)]})
        _fresh(env, post)
        assert post.tag_ids._ids == (t2.id,)
        post.write({"tag_ids": [Command.link(t2.id), Command.link(t1.id)]})
        _fresh(env, post)
        assert post.tag_ids._ids == (t1.id, t2.id)


def test_m2m_read_orders_by_comodel_order():
    with model_test_env(HPost) as env:
        tags = env["h.tag"].create([{"name": n} for n in ("a", "b", "c")])
        post = env["h.post"].create(
            {"name": "p", "tag_ids": [Command.set([tags[2].id, tags[0].id])]}
        )
        _fresh(env, post)
        assert post.tag_ids._ids == (tags[0].id, tags[2].id)


def test_m2m_active_test_semantics():
    with model_test_env(HPost) as env:
        t1 = env["h.tag"].create({"name": "t1"})
        t2 = env["h.tag"].create({"name": "t2"})
        post = env["h.post"].create(
            {"name": "p", "tag_ids": [Command.set([t1.id, t2.id])]}
        )
        t2.active = False
        _fresh(env, post)
        assert post.tag_ids._ids == (t1.id,)
        both = post.with_context(active_test=False).tag_ids
        assert both._ids == (t1.id, t2.id)
        post.write({"tag_ids": [Command.set([t1.id])]})
        _fresh(env, post)
        assert post.with_context(active_test=False).tag_ids._ids == (t1.id,)
        assert env.cr.storage.get_row_count("h_post_h_tag_rel") == 1


def test_m2m_clear_command_empties_relation():
    with model_test_env(HPost) as env:
        t1 = env["h.tag"].create({"name": "t1"})
        post = env["h.post"].create({"name": "p", "tag_ids": [Command.link(t1.id)]})
        post.write({"tag_ids": [Command.clear()]})
        _fresh(env, post)
        assert not post.tag_ids
        assert env.cr.storage.get_row_count("h_post_h_tag_rel") == 0


def test_translated_field_reads_back_after_invalidate():
    with model_test_env(HBook) as env:
        book = env["h.book"].create({"title": "Hello"})
        _fresh(env, book)
        assert book.title == "Hello"
        found = env["h.book"].search([("title", "=", "Hello")])
        assert found._ids == (book.id,)
        stored = env.cr.storage.get_row("h_book", book.id)["title"]
        assert stored == {"en_US": "Hello"}


def test_translated_field_update_path_merges_and_unwraps():
    with model_test_env(HBook) as env:
        book = env["h.book"].create({"title": "Hello"})
        _fresh(env, book)
        book.title = "World"
        _fresh(env, book)
        assert book.title == "World"
        stored = env.cr.storage.get_row("h_book", book.id)["title"]
        assert isinstance(stored, dict)
        assert stored["en_US"] == "World"


def test_commit_flushes_and_runs_postcommit_hooks():
    with model_test_env(HWidget) as env:
        fired = []
        env.cr.postcommit.add(lambda: fired.append("post"))
        rec = env["h.widget"].create({"name": "A"})
        rec.qty = 7
        env.cr.commit()
        assert fired == ["post"]
        assert env.cr.storage.get_row("h_widget", rec.id)["qty"] == 7
        assert not env.cr.precommit
        assert rec.qty == 7


def test_rollback_fails_loud():
    with model_test_env(HWidget) as env:
        env["h.widget"].create({"name": "A"})
        with pytest.raises(InMemorySqlNotSupported):
            env.cr.rollback()


def test_savepoint_rolls_the_storage_back_to_its_snapshot():
    with model_test_env(HWidget) as env:
        kept = env["h.widget"].create({"name": "kept"})
        with pytest.raises(ValueError):
            with env.cr.savepoint():
                env["h.widget"].create({"name": "dropped"})
                kept.name = "renamed inside"
                raise ValueError("boom")
        names = env["h.widget"].search([]).mapped("name")
        assert names == ["kept"], names
        with env.cr.savepoint(flush=False) as sp:
            env["h.widget"].create({"name": "dropped too"})
            env.flush_all()
            sp.rollback()
        assert env["h.widget"].search_count([]) == 1


def test_savepoint_keeps_what_completes_and_refuses_a_commit_inside():
    with model_test_env(HWidget) as env:
        with env.cr.savepoint():
            env["h.widget"].create({"name": "committed"})
            with pytest.raises(RuntimeError, match="commit inside a savepoint"):
                env.cr.commit()
        assert env["h.widget"].search([]).mapped("name") == ["committed"]


def test_clear_cache_honors_names():
    with model_test_env(HWidget) as env:
        caches = env.registry.ormcache_lrus
        caches["default"]["k"] = 1
        caches["templates.cached_values"]["k"] = 1
        caches["assets"]["k"] = 1
        env.registry.clear_cache()
        assert not caches["default"]
        assert not caches["templates.cached_values"]
        assert caches["assets"] == {"k": 1}
        env.registry.clear_cache("assets")
        assert not caches["assets"]
        with pytest.raises(ValueError):
            env.registry.clear_cache("templates.cached_values")


def test_discard_fields_works_without_attributeerror():
    registry = ModelRegistry([HWidget])
    field = registry["h.widget"]._fields["total"]
    registry.discard_fields([field])
    assert field not in registry.field_depends


class HAudit(models.Model):
    _name = "h.audit"
    _module = _MOD
    _description = "log-access model"

    name = fields.Char()


def test_now_is_transaction_stable():
    with model_test_env(HAudit) as env:
        first = env.cr.now()
        assert env.cr.now() is first
        a = env["h.audit"].create({"name": "a"})
        b = env["h.audit"].create({"name": "b"})
        assert a.create_date == b.create_date == first
        env.cr.commit()
        second = env.cr.now()
        assert second is not first
        assert second >= first
        assert env.cr.now() is second


def test_write_after_invalidate_with_log_access():
    with model_test_env(HAudit) as env:
        record = env["h.audit"].create({"name": "a"})
        env.invalidate_all()
        record.write({"name": "b"})
        assert record.name == "b"
        assert record.write_uid.id == 1
        assert env["res.users"].browse(1).login == "admin"


def test_user_supplied_res_users_wins_over_stub():
    class MyUsers(models.Model):
        _name = "res.users"
        _module = _MOD
        _description = "custom users"
        _log_access = False

        name = fields.Char()
        custom_flag = fields.Boolean()

    with model_test_env(HAudit, MyUsers) as env:
        assert "custom_flag" in env["res.users"]._fields


def test_langs_do_not_leak_into_a_reused_registry():
    registry = ModelRegistry((HWidget,), db_name=":memory:")
    default_locale = type(registry).locale
    with model_test_env(HWidget, registry=registry, langs=("en_US", "fr_FR")):
        assert "locale" in registry.__dict__
    assert "locale" not in registry.__dict__
    with model_test_env(HWidget, registry=registry) as env:
        assert env.registry.locale is default_locale
