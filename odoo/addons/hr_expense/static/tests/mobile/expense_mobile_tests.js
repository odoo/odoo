/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

import { registry } from "@web/core/registry";
import { makeFakeHTTPService } from "@web/../tests/helpers/mock_services";

const serviceRegistry = registry.category("services");

let target;
let serverData;

QUnit.module("Expense", (hooks) => {
    hooks.beforeEach(() => {
        serviceRegistry.add("http", makeFakeHTTPService());
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                    },
                },
            },
        };
    });

    QUnit.test("expense dashboard can horizontally scroll", async function (assert) {
        // for this test, we need the elements to be visible in the viewport
        target = document.body;
        target.classList.add("debug");
        registerCleanup(() => target.classList.remove("debug"));

        serverData.views = {
            "partner,false,search": `<search/>`,
            "partner,false,list": `
                <tree js_class="hr_expense_dashboard_tree">
                    <field name="display_name"/>
                </tree>
            `,
        };

        const webclient = await createWebClient({
            serverData,
            target,
            async mockRPC(_, { method }) {
                if (method === "get_expense_dashboard") {
                    return {
                        draft: {
                            description: "to report",
                            amount: 1000000000.00,
                            currency: 2,
                        },
                        reported: {
                            description: "under validation",
                            amount: 1000000000.00,
                            currency: 2,
                        },
                        approved: {
                            description: "to be reimbursed",
                            amount: 1000000000.00,
                            currency: 2,
                        },
                    };
                }
            },
        });
        await doAction(webclient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });
        const statusBar = target.querySelector(".o_expense_container");
        statusBar.scrollLeft = 20;
        await nextTick();
        assert.strictEqual(
            statusBar.scrollLeft,
            20,
            "the o_content should be 20 due to the overflow auto"
        );
    });
});
