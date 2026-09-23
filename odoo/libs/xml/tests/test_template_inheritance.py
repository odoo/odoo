import pytest
from lxml import etree

from odoo.libs.xml.template_inheritance import (
    XPathExpressionError,
    apply_inheritance_specs,
    locate_node,
)


def _apply(original: str, *, remove: str, separator: str = "and", add: str = "") -> str:
    arch = etree.fromstring(f'<form><field name="a" invisible="{original}"/></form>')
    add_attr = f' add="{add}"' if add else ""
    spec = etree.fromstring(
        f'<field name="a" position="attributes">'
        f'<attribute name="invisible" remove="{remove}"{add_attr}'
        f' separator="{separator}"/></field>'
    )
    return apply_inheritance_specs(arch, spec)[0].get("invisible", "")


class TestAttributeRemoveIsLiteral:
    def test_exact_match_clears_the_attribute(self):
        assert _apply("state == 'draft'", remove="state == 'draft'") == ""

    def test_alternation_is_not_a_regex_alternative(self):
        assert _apply("a or b", remove="a|b", separator="or") == "a or b"

    def test_dot_is_not_a_wildcard(self):
        assert _apply("axb", remove="a.b") == "axb"

    def test_unbalanced_paren_does_not_raise(self):
        assert _apply("foo", remove="(") == "foo"

    def test_term_removal_still_works(self):
        assert _apply("(a) and (b)", remove="b") == "(a)"
        assert _apply("a and b", remove="b") == "a"

    def test_add_after_remove(self):
        assert _apply("a", remove="a", add="b") == "b"


class TestLocateNode:
    def test_xpath_without_expr_raises_value_error(self):
        arch = etree.fromstring("<form><field name='a'/></form>")
        spec = etree.fromstring('<xpath position="replace"><p/></xpath>')
        with pytest.raises(XPathExpressionError, match="missing 'expr'"):
            locate_node(arch, spec)

    @pytest.mark.parametrize(
        "expr",
        [
            "name(/*)",
            "//field/@name",
            "count(//field)",
            "//field/text()",
            "//comment()",
        ],
    )
    def test_xpath_selecting_a_value_is_refused(self, expr):
        arch = etree.fromstring("<form><!-- c --><field name='a'>t</field></form>")
        spec = etree.fromstring(f'<xpath expr="{expr}" position="replace"/>')
        with pytest.raises(XPathExpressionError, match="must select elements"):
            locate_node(arch, spec)
        with pytest.raises(XPathExpressionError, match="must select elements"):
            apply_inheritance_specs(arch, spec)

    def test_xpath_selecting_nothing_locates_nothing(self):
        arch = etree.fromstring("<form><field name='a'/></form>")
        spec = etree.fromstring('<xpath expr="//group" position="replace"/>')
        assert locate_node(arch, spec) is None


class TestSpecQueue:
    def test_caller_list_is_not_consumed(self):
        arch = etree.fromstring("<form><field name='a'/></form>")
        specs = list(
            etree.fromstring(
                '<data><field name="a" position="attributes">'
                '<attribute name="x">1</attribute></field></data>'
            )
        )
        apply_inheritance_specs(arch, specs)
        assert len(specs) == 1
        arch2 = etree.fromstring("<form><field name='a'/></form>")
        assert apply_inheritance_specs(arch2, specs)[0].get("x") == "1"


class TestRootReplace:
    def test_the_root_is_replaced_by_the_specs_element(self):
        arch = etree.fromstring('<body t-name="page">old</body>')
        spec = etree.fromstring(
            '<xpath expr="/body" position="replace"><body>new</body></xpath>'
        )

        root = apply_inheritance_specs(arch, spec)

        assert (root.tag, root.text, root.get("t-name")) == ("body", "new", "page")

    def test_a_root_replace_holding_no_element_is_refused(self):
        arch = etree.fromstring("<body>old</body>")
        spec = etree.fromstring(
            '<xpath expr="/body" position="replace">only text</xpath>'
        )

        with pytest.raises(ValueError, match="needs an element"):
            apply_inheritance_specs(arch, spec)


class TestAttributeRemoveKeepsTermBoundaries:
    @pytest.mark.parametrize(
        ("original", "remove", "separator", "expected"),
        [
            ("data or b", "a", "or", "data or b"),
            (
                "other_state == 'done' or x",
                "state == 'done'",
                "or",
                "other_state == 'done' or x",
            ),
            ("f(a) or x", "a", "or", "f(a) or x"),
            ("x or ab", "a", "or", "x or ab"),
            ("id == 11 or x", "1", "or", "id == 11 or x"),
            ("id == 11 or 1 or x", "1", "or", "id == 11 or x"),
            ("x or state == 'done'", "state == 'done'", "or", "x"),
            ("1 or not name", "1", "or", "not name"),
            (
                "(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)",
                "id == 2",
                "and",
                "(((id == 1)) and (id == 3)) and (id == 4)",
            ),
            (
                "(((id == 1) and (id == 2)) and (id == 3)) and (id == 4)",
                "id == 3",
                "and",
                "(((id == 1) and (id == 2))) and (id == 4)",
            ),
            (
                "(id == 1) and (id == 2) and (id == 3)",
                "id == 2",
                "and",
                "(id == 1) and (id == 3)",
            ),
        ],
    )
    def test_only_a_whole_term_is_removed(self, original, remove, separator, expected):
        assert _apply(original, remove=remove, separator=separator) == expected


class TestNestedDataOrder:
    def test_a_nested_data_applies_where_it_stands(self):
        arch = etree.fromstring("<form><a/></form>")
        specs = etree.fromstring(
            '<data><a position="after"><b/></a>'
            '<data><a position="after"><c/></a></data>'
            '<a position="after"><d/></a></data>'
        )
        result = apply_inheritance_specs(arch, specs)
        assert [child.tag for child in result] == ["a", "d", "c", "b"]
