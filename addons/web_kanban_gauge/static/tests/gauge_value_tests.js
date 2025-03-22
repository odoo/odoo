/** @odoo-module **/

import { getFixture, getNodesTextContent } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

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
                    },
                    records: [
                        { id: 1, int_field: 10 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("GaugeValue");

    QUnit.test("GaugeValue in kanban view", async function (assert) {
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
                                <field name="int_field" widget="gauge"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsN(target, ".o_field_widget[name=int_field] .oe_gauge canvas", 2);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_gauge_value")), [
            "10",
            "10",
        ]);
    });
});
