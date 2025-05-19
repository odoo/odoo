import ast

from odoo.exceptions import ValidationError


_ALLOWED_FUNCS = ('min', 'max')
_ALLOWED_NAMES = ('price_unit', 'quantity', 'base', 'product')
_ALLOWED_CONSTANT_T = (int, float, type(None))


_NODE_WHITELIST = (
    ast.Expression, ast.Name, ast.Call, ast.Subscript,  # expr
    ast.Constant,                                       # constants
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div,     # binops
    ast.BoolOp, ast.And, ast.Or,                        # boolops
    ast.Compare, ast.Lt, ast.LtE, ast.Gt, ast.GtE,      # comparisons
    ast.UnaryOp, ast.UAdd, ast.USub                     # unary ops
)


class ProductFieldRewriter(ast.NodeTransformer):
    """
    - Rewrites  product.foo -> product['foo']
    - Collects every field name accessed (through product.foo or product['foo'])
    """

    FIELD_NAME = "product"

    def __init__(self) -> None:
        super().__init__()
        self.accessed_fields: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == self.FIELD_NAME
        ):
            # fail early if AST specs ever change
            assert isinstance(node.attr, str), "Attribute name must be a string"

            self.accessed_fields.add(node.attr)
            return ast.Subscript(
                value=node.value,
                slice=ast.Constant(node.attr),
                ctx=node.ctx,
            )
        return node

    def visit_Subscript(self, node: ast.Subscript):
        node = self.generic_visit(node)
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == self.FIELD_NAME
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            self.accessed_fields.add(node.slice.value)
        return node


class TaxFormulaValidator(ast.NodeVisitor):
    """
    Walks AST and rejects anything that is not needed or not reproducible in pyjs.

    The ast must be transformed by ProductFieldRewriter before being passed to this validator as
    this visitor does not whitelist Attribute nodes
    """
    def __init__(self, env):
        self.env = env
        super().__init__()

    def visit(self, node):
        if not isinstance(node, _NODE_WHITELIST):
            raise ValidationError(self.env._("Invalid AST node: %s", type(node).__name__))
        super().visit(node)

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, _ALLOWED_CONSTANT_T):
            raise ValidationError(self.env._("Only int, float or None are allowed as constant values"))

    def visit_Name(self, node: ast.Name):
        if node.id not in _ALLOWED_NAMES:
            raise ValidationError(self.env._("Unknown identifier: %s", str(node.id)))
        if not isinstance(node.ctx, ast.Load):
            raise ValidationError(self.env._("Only read access to identifiers is allowed"))

    def visit_Call(self, node: ast.Call):
        if not (
            isinstance(node.func, ast.Name)
            and node.func.id in _ALLOWED_FUNCS
            and isinstance(node.func.ctx, ast.Load)
        ):
            raise ValidationError(self.env._("Unknown function call"))
        # don't visit node.func: it's already validated and min/max aren't allowed as normal Name identifiers
        for arg in node.args:
            self.visit(arg)
        if node.keywords:
            raise ValidationError(self.env._("Kwargs are not allowed"))

    def visit_Subscript(self, node: ast.Subscript):
        # Only allow string constants as subscripts (e.g., product["type"])
        # They are not allowed elsewhere in the formula
        if not (
            isinstance(node.value, ast.Name)
            and node.value.id == "product"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
            and isinstance(node.ctx, ast.Load)
        ):
            raise ValidationError(self.env._("Only product['string'] read-access is allowed"))

        self.visit(node.value)


def check_formula(env, formula: str) -> str:
    """
    This helper function checks that the formula is compatible with pyjs
    by checking that the AST only uses allowed nodes in the appropriate context
    and raises a ValidationError if not.
    """
    assert isinstance(formula, str), "Formula must be a string"

    try:
        tree = ast.parse(formula, mode="eval")
    except (SyntaxError, ValueError):
        raise ValidationError(env._("Invalid formula"))

    # `env` is needed to generate localized error messages.
    # Odoo's `_()` translation looks for `env` in the caller's local scope and one frame above it,
    # but AST traversal is recursive and hides the original context in a deep frame stack
    TaxFormulaValidator(env).visit(tree)


def normalize_formula(env, formula: str, field_predicate=None) -> tuple[str, set[str]]:
    """
    This helper function collects all field access and rewrites
    all attribute accesses to product to subscript accesses

    e.g.: product.field to product['field'] access & collect all accessed product fields.

    :return (normalized formula, set of accessed product attributes & fields)
    """
    assert isinstance(formula, str), "Formula must be a string"

    try:
        tree = ast.parse(formula, mode="eval")
    except (SyntaxError, ValueError):
        raise ValidationError(env._("Invalid formula"))

    transformer = ProductFieldRewriter()
    transformed_tree = transformer.visit(tree)
    ast.fix_missing_locations(transformed_tree)  # puts back lineno/col_offset for safe_eval's compile

    if callable(field_predicate):
        for field in transformer.accessed_fields:
            if not field_predicate(field):
                raise ValidationError(env._("Field '%s' is not accessible", field))

    return ast.unparse(transformed_tree), transformer.accessed_fields
