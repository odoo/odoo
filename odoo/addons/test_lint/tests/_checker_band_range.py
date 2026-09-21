import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

# A model that declares a numeric pair `<x>_min`/`<x>_max` (or `min_<x>`/`max_<x>`)
# and classifies a value by it has rolled a band by hand: inclusive on both ends
# in one model, half-open in the next, an integer pair over a float score with
# a gap between 79 and 80 that proposed no grade (account_credit, 2026-09-21).
# `mixin.band` owns the range: half-open, overlap-checked, scoped.
#
# Ratcheted, not zero: a tolerance, a slider, a filter bound or a size range is
# a pair too and not a scale, so the floor names the debt and only a scale that
# classifies should move onto the mixin.

NUMERIC = frozenset({"Float", "Integer", "Monetary"})
PAIR = re.compile(r"^(?:(?P<a>.+)_min|min_(?P<b>.+))$")


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def _inherits_band(class_node: ast.ClassDef) -> bool:
    for statement in class_node.body:
        match statement:
            case ast.Assign(targets=[ast.Name(id="_inherit")], value=value):
                match value:
                    case ast.Constant(value="mixin.band"):
                        return True
                    case ast.List(elts=elts) | ast.Tuple(elts=elts):
                        if any(
                            isinstance(elt, ast.Constant) and elt.value == "mixin.band"
                            for elt in elts
                        ):
                            return True
                        # a scale mixin is a band: the concrete model inherits it
                        if any(
                            isinstance(elt, ast.Constant)
                            and isinstance(elt.value, str)
                            and elt.value.startswith("mixin.score.")
                            for elt in elts
                        ):
                            return True
    return False


def _numeric_fields(class_node: ast.ClassDef) -> dict[str, ast.Assign]:
    found = {}
    for statement in class_node.body:
        match statement:
            case ast.Assign(
                targets=[ast.Name(id=name)],
                value=ast.Call(
                    func=ast.Attribute(value=ast.Name(id="fields"), attr=kind)
                ),
            ) if kind in NUMERIC:
                found[name] = statement
    return found


def _partner_of(name: str) -> str | None:
    match = PAIR.match(name)
    if match is None:
        return None
    if match.group("a") is not None:
        return f"{match.group('a')}_max"
    return f"max_{match.group('b')}"


def check(tree: ast.Module) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or _inherits_band(node):
            continue
        numeric = _numeric_fields(node)
        for name, statement in numeric.items():
            partner = _partner_of(name)
            if partner is None or partner not in numeric:
                continue
            yield Violation(
                statement.lineno,
                statement.col_offset,
                f"{name}/{partner} is a hand-rolled range; a range that classifies "
                f"a value is a mixin.band",
            )
