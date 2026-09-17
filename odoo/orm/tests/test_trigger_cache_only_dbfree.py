from unittest import mock

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_trigger_cache_only"


class View(models.Model):
    _name = "tco.view"
    _module = _MOD
    _description = "view"
    _log_access = False

    name = fields.Char()
    page_ids = fields.One2many("tco.page", "view_id")


class Page(models.Model):
    _name = "tco.page"
    _module = _MOD
    _description = "page"
    _log_access = False

    view_id = fields.Many2one("tco.view")
    view_name = fields.Char(related="view_id.name")


class _PagesRead:
    """How many times the traversal reached for a view's page_ids."""

    def __init__(self, env):
        self.cls = type(env["tco.view"])
        self.count = 0

    def __enter__(self):
        original = self.cls.__getitem__

        def spy(record, key):
            if key == "page_ids":
                self.count += 1
            return original(record, key)

        self.patch = mock.patch.object(self.cls, "__getitem__", spy)
        self.patch.start()
        return self

    def __exit__(self, *exc):
        self.patch.stop()


def _pages_read(env):
    return _PagesRead(env)


def test_a_cache_only_dependent_is_invalidated_without_fetching_the_x2many():
    with model_test_env(View, Page) as env:
        view = env["tco.view"].create({"name": "one"})
        page = env["tco.page"].create({"view_id": view.id})
        other = env["tco.page"].create({"view_id": view.id})
        env.flush_all()
        assert page.view_name == "one"  # cached now
        with _pages_read(env) as read:
            view.name = "two"
        assert read.count == 0, "page_ids was fetched to invalidate view_name"
        assert page.view_name == "two"
        assert other.view_name == "two"


def test_a_dependent_of_another_view_keeps_its_cache():
    with model_test_env(View, Page) as env:
        first = env["tco.view"].create({"name": "one"})
        second = env["tco.view"].create({"name": "other"})
        mine = env["tco.page"].create({"view_id": first.id})
        theirs = env["tco.page"].create({"view_id": second.id})
        env.flush_all()
        assert (mine.view_name, theirs.view_name) == ("one", "other")
        field = env["tco.page"]._fields["view_name"]
        first.name = "two"
        assert env.cache.contains(theirs, field), (
            "the other view's page was invalidated too"
        )
        assert not env.cache.contains(mine, field)
        assert mine.view_name == "two"


def test_nothing_cached_means_nothing_to_do():
    with model_test_env(View, Page) as env:
        view = env["tco.view"].create({"name": "one"})
        env["tco.page"].create({"view_id": view.id})
        env.flush_all()
        env.invalidate_all()
        with _pages_read(env) as read:
            view.name = "two"
        assert read.count == 0
