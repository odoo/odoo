/** @odoo-module **/

import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
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
        assert.expect(2);

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
        assert.containsNone(target, ".o_cp_buttons > .btn-primary");
    });

    QUnit.test("Traceability Report action contains correct url in context", async function (assert) {
        assert.expect(1);
        const webClient = await createWebClient({
            serverData,
            mockRPC: async function (route) {
                if (route === "/web/dataset/call_kw/stock.traceability.report/get_main_lines") {
                    return [
                        {
                            id: 42,
                            model: "stock.move.line",
                            model_id: 42,
                            parent_id: false,
                            usage: "out",
                            is_used: true,
                            lot_name: "0001",
                            lot_id: 1,
                            reference: "WH/MO/00001",
                            res_id: 4,
                            res_model: "mrp.production",
                            columns: [
                                "WH/MO/00001",
                                "Engine",
                                "06/08/2025 15:00:00",
                                "0000000010001",
                                "Stock",
                                "Production",
                                "1.00 Units",
                            ],
                            level: 1,
                            unfoldable: false,
                        },
                    ];
                }
            },
        });
        patchWithCleanup(webClient.env.services.action, {
            doAction(action) {
                const res = super.doAction(...arguments);
                if (action?.type === "ir.actions.client") {
                    assert.strictEqual(
                        "/stock/output_format/stock?active_id=:active_id&active_model=:active_model",
                        action.context.url
                    );
                }
                return res;
            },
        });
        await doAction(webClient, 42);
        await click(target.querySelector(".fa-level-up"));
    });
});
