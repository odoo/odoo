/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(() => {
        makeViewParams = {
            type: "kanban",
            resModel: "project.update",
            serverData: {
                models: {
                    "project.update": {
                        fields: {
                            id: {string: "Id", type: "integer"},
                            status: {
                                string: "Status",
                                type: "selection",
                                selection: [
                                    ["on_track", "On Track"],
                                    ["at_risk", "At Risk"],
                                    ["off_track", "Off Track"],
                                    ["on_hold", "On Hold"],
                                    ["done", "Done"],
                                ],
                            },
                        },
                        records: [
                            {id: 1, status: "on_track"},
                        ],
                    },
                },
            },
            arch: `
                <kanban  class="o_kanban_test">
                    <template>
                        <t t-name="card">
                            <field name="status" widget="status_with_color" readonly="1" status_label="test status label"/>
                        </t>
                    </template>
                </kanban>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.module("Components", (hooks) => {
        QUnit.module("ProjectStatusWithColorSelection");
        QUnit.test("Check that ProjectStatusWithColorSelectionField is displaying the correct informations", async function (assert) {
            await makeView(makeViewParams);

            assert.containsOnce(target, 'div[name="status"] .o_color_bubble_20', "In readonly a status bubble should be displayed")
            assert.containsOnce(target, 'div[name="status"] .o_stat_text:contains("test status label")', "If the status_label prop has been set, its value should be displayed as well")
            assert.containsOnce(target, 'div[name="status"] .o_stat_value:contains("On Track")', "The value of the selection should be displayed")
        });
    });
});
