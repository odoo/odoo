/* @odoo-module */

import { getFixture, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let makeViewParams, target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(() => {
        makeViewParams = {
            type: "form",
            resModel: "project.task",
            serverData: {
                models: {
                    "project.task": {
                        fields: {
                            id: {string: "Id", type: "integer"},
                            priority: {
                                string: "Priority",
                                type: "selection",
                                selection: [
                                    ["0", "Low"],
                                    ["1", "High"],
                                ],
                            },
                        },
                        records: [
                            { id: 1, priority: "0" },
                        ],
                    },
                },
            },
            arch: `
                <form class="o_kanban_test">
                    <field name="priority" widget="priority_switch"/>
                </form>`,
        };
        target = getFixture();
        setupViewRegistries();
    });
    QUnit.module("Components", (hooks) => {
        QUnit.module("ProjectTaskPrioritySwitch");
        QUnit.test("Check whether task priority shortcut works as intended", async function (assert) {
            await makeView(makeViewParams);

            assert.containsOnce(target, 'div[name="priority"] .fa-star-o', "The low priority should display the fa-star-o (empty) icon");
            await triggerHotkey("alt+r");
            assert.containsOnce(target, 'div[name="priority"] .fa-star', "After using the alt+r hotkey the priority should be set to high and the widget should display the fa-star (filled) icon");
        });
    });
});
