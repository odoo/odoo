/** @odoo-module */

import { getFixture, click } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Project", (hooks) => {
        hooks.beforeEach(() => {
        makeViewParams = {
            type: "kanban",
            resModel: "project.project",
            serverData: {
                models: {
                    "project.project": {
                        fields: {
                            id: {string: "Id", type: "integer"},
                            last_update_status: {
                                string: "Status",
                                type: "selection",
                                selection: [
                                    ["on_track", "On Track"],
                                    ["at_risk", "At Risk"],
                                    ["off_track", "Off Track"],
                                    ["on_hold", "On Hold"],
                                    ["to_define", "Set Status"],
                                ],
                            },
                            last_update_color: {
                                string: "Update State Color",
                                type: "integer",
                            },
                        },
                        records: [
                            {id: 1, last_update_status: "on_track", last_update_color: 20},
                        ],
                    },
                },
            },
            arch: `
                <kanban  class="o_kanban_test">
                    <field name="last_update_status"/>
                    <field name="last_update_color"/>
                    <template>
                        <t t-name="kanban-box">
                            <div>
                                <field name="last_update_status" widget="project_state_selection"/>
                            </div>
                        </t>
                    </template>
                </kanban>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
        QUnit.module("Components", (hooks) => {
            QUnit.module("ProjectStateSelectionField");
            QUnit.test("Check that ProjectStateSelectionField does not propose `Set Status`", async function (assert) {
                await makeView(makeViewParams);
                await click(target, 'div[name="last_update_status"] button.dropdown-toggle');
                assert.containsNone(target, 'div[name="last_update_status"] .dropdown-menu .dropdown-item:contains("Set Status")');
            });
        });
    });
