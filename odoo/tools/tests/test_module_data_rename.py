import unittest

from odoo.tools.module_data import _FieldRename, _ModuleRename, _rename_in_arch

COMODELS = {
    ("sale.order", "order_line"): "sale.order.line",
    ("sale.order", "partner_id"): "res.partner",
    ("sale.order.line", "order_id"): "sale.order",
    ("res.partner", "user_id"): "res.users",
    ("res.partner", "parent_id"): "res.partner",
}


def rename_field(arch, old, new, model, view_model="sale.order", comodels=COMODELS):
    return _rename_in_arch(arch, view_model, _FieldRename(old, new, model, comodels))


class TestModuleRenameReachesXmlIdsOnly(unittest.TestCase):
    def setUp(self):
        self.rename = _ModuleRename("iot", "iot_core")

    def test_every_xml_id_position_of_an_arch_follows(self):
        arch = (
            '<form><button name="%(iot.action_box)d" type="action" '
            'groups="base.group_user, !iot.group_manager"/>'
            '<button name="iot.action_scan" type="action"/>'
            '<t t-call="iot.template"/><t t-call-assets="iot.assets"/>'
            '<t t-snippet="iot.s_box"/><t t-install="iot"/>'
            "<field name=\"box_id\" context=\"{'default_x': ref('iot.box_one')}\"/>"
            '<attribute name="groups" add="iot.group_user" remove="iot.group_x"/>'
            '<attribute name="groups">iot.group_admin</attribute></form>'
        )
        renamed = self.rename.in_arch(arch)
        self.assertNotIn('"iot.', renamed)
        self.assertNotIn("'iot.", renamed)
        for expected in (
            'name="%(iot_core.action_box)d"',
            'groups="base.group_user, !iot_core.group_manager"',
            'name="iot_core.action_scan"',
            't-call="iot_core.template"',
            't-call-assets="iot_core.assets"',
            't-snippet="iot_core.s_box"',
            't-install="iot_core"',
            "ref('iot_core.box_one')",
            'add="iot_core.group_user" remove="iot_core.group_x"',
            ">iot_core.group_admin</attribute>",
        ):
            self.assertIn(expected, renamed)

    def test_a_model_name_the_module_prefix_opens_is_left_alone(self):
        arch = (
            "<form><field name=\"box_id\" context=\"{'m': 'iot.box'}\" "
            "domain=\"[('model', '=', 'iot.box')]\"/>"
            '<div data-oe-model="iot.box" t-if="env[\'iot.box\']"/>'
            '<button name="action_open" type="object"/></form>'
        )
        self.assertEqual(self.rename.in_arch(arch), arch)

    def test_stored_code_renames_the_reference_and_keeps_the_model(self):
        code = (
            "tpl = env.ref('iot.template_x')\n"
            "box = self.env['ir.model.data']._xmlid_to_res_id(\"iot.box_one\")\n"
            "boxes = env['iot.box'].search([])\n"
            "record.message_post(body='see iot.box')"
        )
        self.assertEqual(
            self.rename.in_text(code),
            "tpl = env.ref('iot_core.template_x')\n"
            "box = self.env['ir.model.data']._xmlid_to_res_id(\"iot_core.box_one\")\n"
            "boxes = env['iot.box'].search([])\n"
            "record.message_post(body='see iot.box')",
        )

    def test_a_module_whose_name_ends_another_is_not_touched(self):
        self.assertEqual(
            self.rename.in_text("env.ref('pos_iot.x'); env.ref('myiot.y')"),
            "env.ref('pos_iot.x'); env.ref('myiot.y')",
        )


class TestFieldRenameScopesAnArch(unittest.TestCase):
    def test_a_node_placed_beside_a_relational_field_is_the_view_model(self):
        arch = (
            '<data><field name="order_line" position="after">'
            '<field name="note"/></field></data>'
        )
        self.assertIn('name="memo"', rename_field(arch, "note", "memo", "sale.order"))
        self.assertEqual(rename_field(arch, "note", "memo", "sale.order.line"), arch)

    def test_a_node_placed_inside_a_relational_field_is_the_comodel(self):
        arch = (
            '<data><field name="order_line"><list><field name="note"/></list>'
            "</field></data>"
        )
        self.assertEqual(rename_field(arch, "note", "memo", "sale.order"), arch)
        self.assertIn(
            'name="memo"', rename_field(arch, "note", "memo", "sale.order.line")
        )

    def test_a_field_domain_is_the_comodel_and_its_values_the_view_model(self):
        arch = (
            "<form><field name=\"partner_id\" domain=\"[('is_company', '=', "
            'is_company)]"/><field name="is_company"/></form>'
        )
        self.assertEqual(
            rename_field(arch, "is_company", "is_org", "sale.order"),
            "<form><field name=\"partner_id\" domain=\"[('is_company', '=', "
            'is_org)]"/><field name="is_org"/></form>',
        )
        self.assertEqual(
            rename_field(arch, "is_company", "is_org", "res.partner"),
            "<form><field name=\"partner_id\" domain=\"[('is_org', '=', "
            'is_company)]"/><field name="is_company"/></form>',
        )

    def test_a_domain_set_through_a_locator_is_the_located_comodel(self):
        arch = (
            '<data><field name="partner_id" position="attributes">'
            "<attribute name=\"domain\">[('is_company', '=', True)]</attribute>"
            '<attribute name="invisible">is_company</attribute></field></data>'
        )
        on_partner = rename_field(arch, "is_company", "is_org", "res.partner")
        self.assertIn("[('is_org', '=', True)]", on_partner)
        self.assertIn(">is_company</attribute>", on_partner)
        on_order = rename_field(arch, "is_company", "is_org", "sale.order")
        self.assertIn("[('is_company', '=', True)]", on_order)
        self.assertIn(">is_org</attribute>", on_order)

    def test_a_path_segment_is_renamed_on_the_model_it_reads(self):
        arch = (
            '<form><field name="partner_id" invisible="not partner_id.user_id"/>'
            '<field name="user_id"/></form>'
        )
        self.assertEqual(
            rename_field(arch, "user_id", "salesman_id", "sale.order"),
            '<form><field name="partner_id" invisible="not partner_id.user_id"/>'
            '<field name="salesman_id"/></form>',
        )
        self.assertEqual(
            rename_field(arch, "user_id", "salesman_id", "res.partner"),
            '<form><field name="partner_id" invisible="not partner_id.salesman_id"/>'
            '<field name="user_id"/></form>',
        )

    def test_parent_reads_the_model_of_the_enclosing_view(self):
        arch = (
            '<form><field name="order_line"><list>'
            '<field name="x" readonly="parent.user_id and user_id"/>'
            "</list></field></form>"
        )
        self.assertIn(
            'readonly="parent.salesman_id and user_id"',
            rename_field(arch, "user_id", "salesman_id", "sale.order"),
        )

    def test_a_path_walks_the_renamed_field_under_either_spelling(self):
        arch = (
            '<search><filter name="f" '
            "domain=\"[('parent_id.parent_id', '=', False)]\"/></search>"
        )
        moved = {**COMODELS, ("res.partner", "parent_partner_id"): "res.partner"}
        del moved[("res.partner", "parent_id")]
        for comodels in (COMODELS, moved):
            with self.subTest(field_row_renamed=comodels is moved):
                self.assertIn(
                    "'parent_partner_id.parent_partner_id'",
                    rename_field(
                        arch,
                        "parent_id",
                        "parent_partner_id",
                        "res.partner",
                        "res.partner",
                        comodels,
                    ),
                )

    def test_an_indented_multi_line_expression_parses(self):
        arch = (
            '<data><xpath expr="//field[@name=\'a\']" position="attributes">'
            '<attribute name="invisible">\n   user_id and\n   partner_id.user_id\n'
            "</attribute></xpath></data>"
        )
        self.assertIn(
            ">\n   salesman_id and\n   partner_id.user_id\n<",
            rename_field(arch, "user_id", "salesman_id", "sale.order"),
        )

    def test_a_qweb_expression_keeps_the_word_rewrite(self):
        arch = "<t t-name='x'><t t-foreach='partner.comment' t-as='line'/></t>"
        self.assertIn(
            't-foreach="partner.notes"',
            rename_field(arch, "comment", "notes", "res.partner", "res.partner"),
        )


class TestFieldRenameInAStoredDomain(unittest.TestCase):
    def rename(self, source, old, new, model, row_model):
        return _FieldRename(old, new, model, COMODELS).expression(
            source, names=None, strings=row_model, leaves=row_model
        )

    def test_a_rule_path_through_a_comodel_follows_and_variables_do_not(self):
        domain = (
            "[('partner_id.user_id', '=', user.id), ('user_id', '=', user.user_id.id)]"
        )
        self.assertEqual(
            self.rename(domain, "user_id", "salesman_id", "res.partner", "sale.order"),
            "[('partner_id.salesman_id', '=', user.id), "
            "('user_id', '=', user.user_id.id)]",
        )
        self.assertEqual(
            self.rename(domain, "user_id", "salesman_id", "sale.order", "sale.order"),
            "[('partner_id.user_id', '=', user.id), "
            "('salesman_id', '=', user.user_id.id)]",
        )

    def test_a_value_that_spells_the_name_is_a_value(self):
        domain = "[('state', '=', 'user_id')]"
        self.assertEqual(
            self.rename(domain, "user_id", "salesman_id", "sale.order", "sale.order"),
            domain,
        )

    def test_a_group_by_and_a_sort_name_their_first_segment(self):
        self.assertEqual(
            self.rename(
                "{'group_by': ['user_id', 'partner_id.user_id']}",
                "user_id",
                "salesman_id",
                "sale.order",
                "sale.order",
            ),
            "{'group_by': ['salesman_id', 'partner_id.user_id']}",
        )
        self.assertEqual(
            self.rename(
                '["user_id desc"]', "user_id", "salesman_id", "sale.order", "sale.order"
            ),
            '["salesman_id desc"]',
        )


if __name__ == "__main__":
    unittest.main()
