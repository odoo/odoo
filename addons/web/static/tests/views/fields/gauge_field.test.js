import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";

class Partner extends models.Model {
    int_field = fields.Integer({ string: "int_field" });
    another_int_field = fields.Integer({ string: "another_int_field" });
    _records = [
        { id: 1, int_field: 10, another_int_field: 45 },
        { id: 2, int_field: 4, another_int_field: 10 },
    ];
}
defineModels([Partner]);

test("GaugeField in kanban view", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
        <kanban>
            <field name="another_int_field"/>
            <templates>
                <t t-name="card">
                    <field name="int_field" widget="gauge" options="{'max_field': 'another_int_field'}"/>
                </t>
            </templates>
        </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_field_widget[name=int_field] .oe_gauge canvas").toHaveCount(2);
    expect(queryAllTexts(".o_gauge_value")).toEqual(["10", "4"]);
});
