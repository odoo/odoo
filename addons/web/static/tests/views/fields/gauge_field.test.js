import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { onMounted } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { GaugeField } from "@web/views/fields/gauge/gauge_field";
import { setupChartJsForTests } from "../graph/graph_test_helpers";

class Partner extends models.Model {
    int_field = fields.Integer({ string: "int_field" });
    another_int_field = fields.Integer({ string: "another_int_field" });
    _records = [
        { id: 1, int_field: 10, another_int_field: 45 },
        { id: 2, int_field: 4, another_int_field: 10 },
    ];
}

defineModels([Partner]);

setupChartJsForTests();

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

test("GaugeValue supports max_value option", async () => {
    patchWithCleanup(GaugeField.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                expect.step("gauge mounted");
                expect(this.chart.config.options.plugins.tooltip.callbacks.label({})).toBe(
                    "Max: 120"
                );
            });
        },
    });

    Partner._records = Partner._records.slice(0, 1);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <div>
                            <field name="int_field" widget="gauge" options="{'max_value': 120}"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    expect.verifySteps(["gauge mounted"]);
    expect(".o_field_widget[name=int_field] .oe_gauge canvas").toHaveCount(1);
    expect(".o_gauge_value").toHaveText("10");
});
