from odoo.orm.components.model_graph import ModelGraph
from odoo.orm.runtime._registry_fields import _RegistryFieldsMixin


class _Field:
    def __init__(self, name, model_name, *, comodel_name=None, depends=()):
        self.name = name
        self.model_name = model_name
        self.type = "many2one" if comodel_name else "integer"
        self.is_many2one = bool(comodel_name)
        self.is_one2many = False
        self.store = True
        self.relational = bool(comodel_name)
        self.compute = "_compute" if depends else None
        self.recursive = False
        self.inverse_name = None
        self.comodel_name = comodel_name
        self.base_field = self
        self.manual = False
        self._depends = depends

    @property
    def is_stored_computed(self):
        return bool(self.store and self.compute)

    def resolve_depends(self, registry):
        yield from self._depends

    def setup_inverses(self, registry, inverses):
        pass

    def __repr__(self):
        return f"<{self.model_name}.{self.name}>"


class _Model:
    def __init__(self, table, root, fields):
        self._abstract = False
        self._table = table
        self._table_inheritance_root = root
        self._fields = {f.name: f for f in fields}


class _Registry(_RegistryFieldsMixin):
    def __init__(self, models, by_root):
        self.models = models
        self.model_graph = ModelGraph()
        self._by_root = by_root

    @property
    def model_names_by_inheritance_root(self):
        return self._by_root


def _tree(n_subtypes: int):
    # a root model and n subtypes, each with its own copy of `days`, which
    # depends on itself through `parent_id` (a many2one to the root model)
    names = ["tree.root"] + [f"tree.sub{i}" for i in range(n_subtypes)]
    models = {}
    root_days = None
    for name in names:
        table = name.replace(".", "_")
        parent = _Field("parent_id", name, comodel_name="tree.root")
        days = _Field("days", name)
        models[name] = _Model(table, "tree_root", [parent, days])
        if name == "tree.root":
            root_days = days
    for name in names:
        model = models[name]
        model._fields["days"]._depends = [(model._fields["parent_id"], root_days)]
    return _Registry(models, {"tree_root": tuple(names)}), models


def test_sibling_copies_of_a_root_column_share_one_fact():
    registry, models = _tree(2)
    root, sub = models["tree.root"], models["tree.sub0"]
    fact = registry._trigger_fact_of(root._fields["days"])
    assert fact == ("tree_root", "days")
    assert registry._trigger_fact_of(sub._fields["days"]) == fact
    assert registry._trigger_fact_of(sub._fields["parent_id"]) == fact[:1] + (
        "parent_id",
    )


def test_a_field_outside_a_tree_is_its_own_fact():
    registry = _Registry({"m": _Model("m", "", [_Field("x", "m")])}, {})
    field = registry.models["m"]._fields["x"]
    assert registry._trigger_fact_of(field) is field


def test_a_subtype_only_field_is_its_own_fact():
    registry, models = _tree(1)
    own = _Field("only_here", "tree.sub0")
    models["tree.sub0"]._fields["only_here"] = own
    assert registry._trigger_fact_of(own) is own


def _count(tree) -> int:
    return 1 + sum(_count(child) for child in tree.values())


def test_nine_siblings_cost_one_level_not_a_factorial():
    registry, models = _tree(8)
    triggers = registry._get_field_triggers()
    days = models["tree.root"]._fields["days"]
    assert days in triggers
    tree = registry.get_field_trigger_tree(days)
    assert _count(tree) == 1 + 9
    listed = sorted(repr(f) for child in tree.values() for f in child.root)
    assert listed == sorted(repr(m._fields["days"]) for m in models.values())
