/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";

let serverData;
let target;

QUnit.module("Stock", {}, function (hooks) {
    hooks.beforeEach(() => {
        serverData = {
            actions: {
                42: {
                    id: 42,
                    name: "Stock report",
                    tag: "stock_report_generic",
                    type: "ir.actions.client",
                    context: {},
                    params: {},
                },
            },
        };

        target = getFixture();
    });

    QUnit.module("Traceability report");

    QUnit.test("Rendering with no lines", async function (assert) {
        assert.expect(1);

        const webClient = await createWebClient({
            serverData,
            mockRPC: async function (route) {
                if (route === "/web/dataset/call_kw/stock.traceability.report/get_main_lines") {
                    return [];
                }
            },
        });

        await doAction(webClient, 42);
        assert.strictEqual(
            target.querySelector(".o_stock_reports_page").textContent,
            "No operation made on this lot."
        );
    });
});
