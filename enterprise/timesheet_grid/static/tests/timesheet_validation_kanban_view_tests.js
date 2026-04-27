/* @odoo-module */

import { click, contains } from "@web/../tests/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("timesheet_grid", (hooks) => {
    hooks.beforeEach(async function () {
        setupViewRegistries();
    });

    QUnit.module("timesheet_validation_kanban_view");

    QUnit.test("Should trigger notification on validation", async function (assert) {
        await makeView({
            type: "kanban",
            resModel: "account.analytic.line",
            serverData: {
                models: {
                    "account.analytic.line": {
                        fields: {
                            unit_amount: { string: "Unit Amount", type: "integer" },
                        },
                        records: [{ id: 1, unit_amount: 1 }],
                    },
                },
                views: {
                    "account.analytic.line,false,kanban": `
                        <kanban js_class="timesheet_validation_kanban">
                            <templates>
                                <t t-name="card">
                                    <field name="unit_amount"/>
                                </t>
                            </templates>
                        </kanban>
                    `,
                },
            },
            mockRPC(route, args) {
                if (args.method === "action_validate_timesheet") {
                    assert.step("action_validate_timesheet");
                    return Promise.resolve({
                        params: {
                            type: "danger",
                            message: "dummy message",
                        },
                    });
                }
            },
        });
        await click(".o_control_panel_main_buttons button", { text: "Validate" });
        await contains(".o_notification:has(.o_notification_bar.bg-danger)", { text: "dummy message" });
        assert.verifySteps(["action_validate_timesheet"]);
    });
});
