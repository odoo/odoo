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
                                <t t-name="kanban-box">
                                    <div><field name="unit_amount"/></div>
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
                            title: "dummy title",
                        },
                    });
                }
            },
        });
        await click(".o_control_panel_collapsed_create button", { text: "Validate" });
        await contains(".o_notification.border-danger", { text: "dummy title" });
        assert.verifySteps(["action_validate_timesheet"]);
    });
});
