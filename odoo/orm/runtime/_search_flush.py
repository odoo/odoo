from collections import defaultdict

from odoo.libs.debug_log import DebugLog

from ..domain.ast import Domain, DomainCondition, DomainCustom, DomainNary, DomainNot
from ..parsing import parse_field_expr, regex_order

_debug = DebugLog(__name__)


class _DependencyCollector:
    def __init__(self):
        self.fields_by_model = defaultdict(set)
        self.seen = set()
        self.opaque = False

    def collect_field(self, records, expression):
        name, prop = parse_field_expr(expression)
        field = records._fields[name]
        key = (records._name, expression)
        if key in self.seen:
            return field
        self.seen.add(key)
        if field.store:
            self.fields_by_model[records._name].add(name)
            if records._table_inheritance_root:
                # every table of the tree reads rows another model of it writes
                self._collect_inheritance_tree(records, name)
        elif field.related:
            target = records
            for part in field.related.split("."):
                related = self.collect_field(target, part)
                if related.relational:
                    target = records.env[related.comodel_name]
        if field.is_one2many:
            self.collect_field(records.env[field.comodel_name], field.inverse_name)
        if prop and field.relational:
            self.collect_field(records.env[field.comodel_name], prop)
        return field

    def _collect_inheritance_tree(self, records, name):
        env = records.env
        for model_name in env._table_inheritance_tree(records._name):
            if name in env[model_name]._fields:
                self.fields_by_model[model_name].add(name)

    def collect_domain(self, records, node):
        if isinstance(node, DomainCustom):
            if node._filtered is None:
                raise NotImplementedError(
                    "In-memory searches require a Python predicate for custom domains"
                )
            self.opaque = True
        elif isinstance(node, DomainNary):
            for child in node.children:
                self.collect_domain(records, child)
        elif isinstance(node, DomainNot):
            self.collect_domain(records, node.child)
        elif isinstance(node, DomainCondition):
            self._collect_condition(records, node)

    def _collect_condition(self, records, node):
        field = self.collect_field(records, node.field_expr)
        if isinstance(node.value, Domain):
            target = records.env[field.comodel_name] if field.relational else records
            self.collect_domain(target, node.value)

    def collect_order(self, records, specification, ordered_fields=frozenset()):
        records._check_qorder(specification)
        for part in specification.split(","):
            match = regex_order.match(part)
            if match is None:
                raise ValueError(f"Invalid order term {part!r}")
            self._collect_order_term(records, match, ordered_fields)

    def _collect_order_term(self, records, match, ordered_fields):
        field = self.collect_field(records, match["field"])
        if field.is_many2one and not match["property"] and field not in ordered_fields:
            target = records.env[field.comodel_name]
            if target._order:
                self.collect_order(target, target._order, ordered_fields | {field})


def flush_search_dependencies(model, domain, order):
    collector = _DependencyCollector()
    collector.collect_domain(model, domain)
    if order:
        collector.collect_order(model, order)
    _debug.logic(
        "search.flush_dependencies",
        model=model._name,
        opaque=collector.opaque,
        models=len(collector.fields_by_model),
        fields=sum(len(f) for f in collector.fields_by_model.values()),
    )
    if collector.opaque:
        model.env.flush_all()
    else:
        for name, fields in collector.fields_by_model.items():
            model.env[name].flush_model(fields)
    return collector.fields_by_model
