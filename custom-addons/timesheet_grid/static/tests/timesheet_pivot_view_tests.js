/** @odoo-module */

import { registry } from "@web/core/registry";

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";

QUnit.module("timesheet_grid", (hooks) => {
    let target;
    hooks.beforeEach(async function (assert) {
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("TimesheetValidationPivotView");

    QUnit.test("validate button basic rendering", async function(assert) {
        const notificationMock = (message, options) => {
            assert.step("notification_triggered");
            return () => {};
        };
        registry.category("services").add("notification", makeFakeNotificationService(notificationMock), {
            force: true,
        });
        await makeView({
            type: "pivot",
            resModel: "account.analytic.line",
            serverData: {
                models: {
                    'account.analytic.line': {
                        fields: {
                            unit_amount: { string: "Unit Amount", type: "integer" },
                        },
                        records: [
                            { id: 1, unit_amount: 1 },
                        ],
                    },
                },
                views: {
                    "account.analytic.line,false,pivot": `
                        <pivot js_class="timesheet_validation_pivot_view">
                            <field name="unit_amount"/>
                        </pivot>
                    `,
                },
            },
            mockRPC(route, args) {
                if (args.method === "action_validate_timesheet") {
                    assert.step("action_validate_timesheet");
                    return Promise.resolve({
                        params: {
                            type: "dummy type",
                            title: "dummy title",
                        },
                    });
                }
            },
        });
        const validateButton = target.querySelector(".o_pivot_buttons .btn");
        assert.strictEqual(validateButton.innerText, "Validate");
        await click(validateButton);
        assert.verifySteps(["action_validate_timesheet", "notification_triggered"]);
    });

});
