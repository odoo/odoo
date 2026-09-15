import unittest

from lxml import etree

from odoo.tools import view_ir
from odoo.tools.view_validation import ir_valid, valid_view


def codes(arch, view_type=None):
    return [
        (i.code, i.kind, i.severity)
        for i in view_ir.get_issues(view_ir.from_string(arch), view_type)
    ]


class TestViewIrValidate(unittest.TestCase):
    def test_a_clean_form_yields_no_issue(self):
        arch = (
            '<form string="Partner"><sheet><group><field name="name" required="1"/>'
            '<field name="parent_id" invisible="not is_company" options="{\'no_create\': True}"/>'
            '</group><notebook><page name="contacts" string="Contacts"><field name="child_ids"/>'
            "</page></notebook></sheet></form>"
        )
        self.assertEqual(codes(arch), [])

    def test_the_view_type_is_inferred_from_the_root(self):
        self.assertEqual(codes('<list><field name="x" optional="show"/></list>'), [])
        self.assertEqual(
            codes('<list editable="sideways"><field name="x"/></list>'),
            [("bad-enum", "list", "error")],
        )

    def test_account_renderer_conditional_column_is_valid(self):
        self.assertEqual(
            codes('<list><field name="quantity" optional="conditional"/></list>'),
            [],
        )

    def test_website_sale_struck_through_price_is_valid_html(self):
        self.assertEqual(
            codes(
                '<form><del class="oe_read_only"><field name="list_price"/></del></form>'
            ),
            [],
        )

    def test_a_grid_takes_buttons(self):
        self.assertEqual(
            codes(
                '<grid><field name="unit_amount" type="measure"/>'
                '<button type="object" name="action_validate" string="Validate"/></grid>'
            ),
            [],
        )

    def test_a_struck_through_price_is_html(self):
        self.assertEqual(
            codes('<form><del class="oe_read_only">10.00</del></form>'), []
        )

    def test_unknown_kind_is_an_error_and_html_is_not(self):
        self.assertEqual(
            codes("<form><bold>x</bold></form>"), [("unknown-kind", "bold", "error")]
        )
        self.assertEqual(codes('<form><strong>x</strong><div class="o"/></form>'), [])

    def test_unknown_attribute_is_a_warning(self):
        self.assertEqual(
            codes('<form><field name="x" String="X"/></form>'),
            [("unknown-attr", "field", "warning")],
        )

    def test_value_types(self):
        self.assertEqual(
            codes('<form><field name="x" nolabel="maybe"/></form>'),
            [("bad-bool", "field", "error")],
        )
        self.assertEqual(
            codes('<form><group col="two"/></form>'), [("bad-int", "group", "error")]
        )
        self.assertEqual(
            codes('<form><field name="x" invisible="not (a"/></form>'),
            [("bad-pyexpr", "field", "error")],
        )
        self.assertEqual(
            codes("<form><field name=\"x\" domain=\"[('a', '=', 1\"/></form>"),
            [("bad-domain", "field", "error")],
        )
        self.assertEqual(
            codes('<pivot><field name="x" type="rowt"/></pivot>'),
            [("bad-enum", "field", "error")],
        )
        self.assertEqual(
            codes('<graph type="scatter"><field name="x" type="measure"/></graph>'), []
        )

    def test_xmlid_references_are_accepted_in_expressions(self):
        arch = "<form><field name=\"x\" domain=\"[('g', 'in', %(base.group_user)d)]\"/></form>"
        self.assertEqual(codes(arch), [])

    def test_required_attributes(self):
        self.assertEqual(
            codes("<form><field/></form>"), [("missing-attr", "field", "error")]
        )
        self.assertEqual(
            codes('<search><filter string="A" domain="[]"/></search>'),
            [("missing-attr", "filter", "error")],
        )

    def test_inheritance_specs_validate_without_a_view_type(self):
        arch = '<data><xpath expr="//field[@name=\'x\']" position="after"><field name="y"/></xpath></data>'
        self.assertEqual(codes(arch), [])
        self.assertEqual(
            codes('<xpath position="sideways"/>'),
            [("missing-attr", "xpath", "error"), ("bad-enum", "xpath", "error")],
        )

    def test_unexpected_child_is_a_warning(self):
        self.assertEqual(
            codes('<form><header><page name="p"/></header></form>'),
            [("unexpected-child", "page", "warning")],
        )
        self.assertEqual(
            codes("<search><sheet/></search>"), [("unknown-kind", "sheet", "error")]
        )

    def test_issue_renders_its_path(self):
        (issue,) = view_ir.get_issues(
            view_ir.from_string("<form><group><field/></group></form>")
        )
        self.assertEqual(
            str(issue), "error missing-attr at field[0/0]: 'name' is required"
        )


class TestViewValidationUsesTheIr(unittest.TestCase):
    def test_valid_view_refuses_what_the_ir_calls_an_error(self):
        with self.assertLogs("odoo.tools.view_validation", "WARNING") as logs:
            self.assertFalse(
                valid_view(etree.fromstring("<form><bold>x</bold></form>"))
            )
            self.assertFalse(
                valid_view(
                    etree.fromstring('<pivot><field name="d" type="rowt"/></pivot>')
                )
            )
        self.assertTrue(any("unknown-kind" in line for line in logs.output))
        self.assertTrue(any("bad-enum" in line for line in logs.output))

    def test_valid_view_keeps_accepting_a_clean_arch_and_undeclared_attributes(self):
        self.assertTrue(
            valid_view(
                etree.fromstring('<form><field name="x" nb_records_shown="3"/></form>')
            )
        )
        self.assertTrue(
            ir_valid(etree.fromstring('<list><field name="x" optional="show"/></list>'))
        )

    def test_a_root_the_ir_does_not_know_is_not_the_ir_s_business(self):
        self.assertTrue(
            ir_valid(etree.fromstring("<my_custom_view><bold/></my_custom_view>"))
        )
