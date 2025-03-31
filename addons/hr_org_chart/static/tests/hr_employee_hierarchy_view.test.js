import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Employee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    parent_id = fields.Many2one({ string: "Manager", relation: "hr.employee" });
    child_ids = fields.One2many({
        string: "Subordinates",
        relation: "hr.employee",
        relation_field: "parent_id",
    });

    _records = [
        { id: 1, name: "Albert", parent_id: false, child_ids: [2, 3] },
        { id: 2, name: "Georges", parent_id: 1, child_ids: [] },
        { id: 3, name: "Josephine", parent_id: 1, child_ids: [4] },
        { id: 4, name: "Louis", parent_id: 3, child_ids: [] },
    ];

    _views = {
        hierarchy: `
            <hierarchy js_class="hr_employee_hierarchy">
                <templates>
                    <t t-name="hierarchy-box">
                        <div class="o_hierarchy_node_header">
                            <field name="name"/>
                        </div>
                        <div>
                            <field name="parent_id"/>
                        </div>
                    </t>
                </templates>
            </hierarchy>
        `,
        form: `
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="parent_id"/>
                    </group>
                </sheet>
            </form>
        `,
    };
}

defineModels([Employee]);
defineMailModels();

test("load hierarchy view", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_view").toHaveCount(1);
    expect(".o_hierarchy_button_add").toHaveCount(1);
    expect(".o_hierarchy_view .o_hierarchy_renderer").toHaveCount(1);
    expect(".o_hierarchy_view .o_hierarchy_renderer > .o_hierarchy_container").toHaveCount(1);
    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_separator").toHaveCount(1);
    expect(".o_hierarchy_line_part").toHaveCount(2);
    expect(".o_hierarchy_line_left").toHaveCount(1);
    expect(".o_hierarchy_line_right").toHaveCount(1);
    expect(".o_hierarchy_node_container").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(3);
    expect(".o_hierarchy_node_button").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-primary.d-grid").toHaveCount(0, {
        message: "'d-grid' class has been removed in that js_class",
    });
    expect(".o_hierarchy_node_button.btn-primary.rounded-0").toHaveCount(0, {
        message: "'d-grid' class has been removed in that js_class",
    });
    expect(".o_hierarchy_node_button.btn-primary .o_hierarchy_icon").toHaveCount(0, {
        message: "the icon has been replaced in that js_class",
    });
    expect(".o_hierarchy_node_button.btn-primary .fa-caret-right").toHaveCount(1, {
        message: "the icon has been replaced in that js_class",
    });
    expect(".o_hierarchy_node_button.btn-primary").toHaveText("1 people");
    // check nodes in each row
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node").toHaveCount(1);
    expect(".o_hierarchy_row:eq(0) .o_hierarchy_node_content").toHaveText("Albert");
    expect(".o_hierarchy_node_button.btn-secondary").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-secondary .fa-caret-down").toHaveCount(1);
    expect(".o_hierarchy_node_button.btn-secondary").toHaveText("2 people");
});

test("display the avatar of the parent when there is more than one node in the same row of the parent", async () => {
    await mountView({
        type: "hierarchy",
        resModel: "hr.employee",
    });

    expect(".o_hierarchy_row").toHaveCount(2);
    expect(".o_hierarchy_node_button.btn-primary").toHaveCount(1);
    await contains(".o_hierarchy_node_button.btn-primary").click();
    expect(".o_hierarchy_row").toHaveCount(3);
    expect(".o_hierarchy_node").toHaveCount(4);
    expect(".o_hierarchy_separator").toHaveCount(2);
    expect(".o_hierarchy_parent_node_container .o_avatar").toHaveCount(1);
    expect(".o_avatar").toHaveText("Josephine");
});
