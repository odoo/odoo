import typing
from collections import defaultdict

from odoo.orm.components.model_graph import ModelGraph
from odoo.orm.runtime._registry_fields import _RegistryFieldsMixin


class _FakeField:
    def __init__(self, name, model_name, depends=()):
        self.name = name
        self.model_name = model_name
        self.type = "integer"
        self.store = True
        self.relational = False
        self.compute = None
        self.recursive = False
        self.inverse_name = None
        self.comodel_name = None
        self.base_field = self
        self.manual = False
        self._depends = depends

    @property
    def is_stored_computed(self):
        return bool(self.store and self.compute)

    def resolve_depends(self, registry):
        yield from self._depends

    def __repr__(self):
        return f"<_FakeField {self.model_name}.{self.name}>"


class _FakeModel:
    def __init__(self, fields):
        self._abstract = False
        self._fields = {f.name: f for f in fields}


class _FakeRegistry(_RegistryFieldsMixin):
    def __init__(self, models):
        self.models = models
        self.model_graph = ModelGraph()

    @property
    def model_names_by_inheritance_root(self):
        return {}


def _registry_with(*, extra_trigger=False):
    a = _FakeField("a", "m")
    b = _FakeField("b", "m", depends=[(a,)])
    fields = [a, b]
    if extra_trigger:
        c = _FakeField("c", "m", depends=[(a,)])
        fields.append(c)
    return _FakeRegistry({"m": _FakeModel(fields)}), a


def test_happy_path_publishes_and_memoizes():
    registry, dep = _registry_with()
    triggers = registry._get_field_triggers()
    assert dep in triggers, "the dependency must appear in the published map"
    assert registry.__dict__["_field_triggers"] is registry.model_graph._triggers


def test_refused_publication_records_the_epoch_it_lost_at():
    registry, _dep = _registry_with()
    registry._get_field_triggers()

    registry.model_graph.begin_invalidation()
    registry.__dict__.pop("_field_triggers", None)

    assert registry._field_triggers is registry.model_graph.published_triggers
    assert "_field_triggers_refused_at" in registry.__dict__


def test_a_refused_memo_goes_permanently_stale_but_the_barrier_heals_it():
    registry, dep = _registry_with()
    registry._get_field_triggers()

    registry.model_graph.begin_invalidation()
    registry.__dict__.pop("_field_triggers", None)
    refused_map = registry._field_triggers
    assert "_field_triggers_refused_at" in registry.__dict__

    registry.model_graph.end_invalidation()
    new_triggers: typing.Any = defaultdict(lambda: defaultdict(list))
    new_field = _FakeField("c", "m")
    new_triggers[dep][()] = [new_field]
    assert registry.model_graph.set_triggers(new_triggers) is True

    assert registry.__dict__["_field_triggers"] is refused_map
    assert refused_map is not registry.model_graph._triggers

    assert new_field not in registry._field_triggers[dep][()]

    healed = registry._get_field_triggers()
    assert healed is registry.model_graph._triggers
    assert healed is not refused_map


def _direct_attribute_reads():
    import ast
    import pathlib

    orm_dir = pathlib.Path(__file__).resolve().parent.parent
    return [
        f"{path.relative_to(orm_dir.parent)}:{node.lineno}"
        for path in orm_dir.rglob("*.py")
        if "tests" not in path.parts and path.name != "_registry_fields.py"
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Attribute) and node.attr == "_field_triggers"
    ]


def test_no_production_caller_reads_the_memo_directly():
    leaking = _direct_attribute_reads()
    assert not leaking, (
        "read `_field_triggers` directly instead of calling "
        "`_get_field_triggers()`: " + ", ".join(leaking)
    )
