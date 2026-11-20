/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { getFixture, getNodesTextContent, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { GaugeField } from "@web/views/fields/gauge/gauge_field";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        int_field: {
                            string: "int_field",
                            type: "integer",
                        },
                        another_int_field: {
                            string: "another_int_field",
                            type: "integer",
                        },
                    },
                    records: [
                        { id: 1, int_field: 10, another_int_field: 45 },
                        { id: 2, int_field: 4, another_int_field: 10 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("GaugeField");

    QUnit.test("GaugeField in kanban view", async function (assert) {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <field name="another_int_field"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" widget="gauge" options="{'max_field': 'another_int_field'}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);
        assert.containsN(target, ".o_field_widget[name=int_field] .oe_gauge canvas", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_gauge_value")), [
            "10",
            "4",
        ]);
    });

    QUnit.test("GaugeValue supports max_value option", async function (assert) {
        patchWithCleanup(GaugeField.prototype, {
            setup() {
                super.setup();
                onMounted(() => {
                    assert.step("gauge mounted");
                    assert.strictEqual(this.chart.config.options.plugins.tooltip.callbacks.label({}), "Max: 120");
                });
            }
        });

        serverData.models.partner.records = serverData.models.partner.records.slice(0,1);
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="int_field" widget="gauge" options="{'max_value': 120}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.verifySteps(["gauge mounted"]);
        assert.containsN(target, ".o_field_widget[name=int_field] .oe_gauge canvas", 1);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_gauge_value")), [
            "10",
        ]);
    });

});
