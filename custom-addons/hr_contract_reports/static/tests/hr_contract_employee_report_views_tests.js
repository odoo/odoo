/** @odoo-module **/

import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { clickOnDataset } from "@web/../tests/views/graph_view_tests";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("HrContractEmployeeReport", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                        },
                    ],
                    onchanges: {},
                },
                test_report: {
                    fields: {
                        categ_id: {
                            string: "categ_id",
                            type: "many2one",
                            relation: "test_report",
                            store: true,
                            sortable: true,
                        },
                        sold: {
                            string: "Sold",
                            type: "float",
                            store: true,
                            group_operator: "sum",
                            sortable: true,
                        },
                        untaxed: {
                            string: "Untaxed",
                            type: "float",
                            group_operator: "sum",
                            store: true,
                            sortable: true,
                        },
                    },
                    records: [
                        {
                            display_name: "First",
                            id: 1,
                            sold: 5,
                            untaxed: 10,
                            categ_id: 1,
                        },
                        {
                            display_name: "Second",
                            id: 2,
                            sold: 3,
                            untaxed: 20,
                            categ_id: 2,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.test(
        "click on HrContractEmployeeReportGraphView opens 'hr.contract' list view",
        async function (assert) {
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "partner",
                arch: "<graph js_class='contract_employee_report_graph'/>",
                mockRPC: async (route, args) => {
                    const { method, model } = args;
                    if (method === "search_read") {
                        assert.step(method);
                        assert.strictEqual(model, "hr.contract.employee.report");
                        return [{ id: 1 }, { id: 2 }];
                    }
                },
            });
            const doAction = graph.env.services.action.doAction;
            patchWithCleanup(graph.env.services.action, {
                doAction: (actionRequest, options) => {
                    const { domain, res_model, views } = actionRequest;
                    if (res_model) {
                        assert.step(`doAction ${res_model}`);
                        assert.deepEqual(domain, [["id", "in", [1, 2]]]);
                        assert.deepEqual(views, [
                            [false, "list"],
                            [false, "form"],
                        ]);
                        return;
                    }
                    doAction(actionRequest, options);
                },
            });
            await clickOnDataset(graph);
            assert.verifySteps(["search_read", "doAction hr.contract"]);
        }
    );

    QUnit.test(
        "click on HrContractEmployeeReportPivotView opens 'hr.contract' list view",
        async function (assert) {
            const graph = await makeView({
                serverData,
                type: "pivot",
                resModel: "partner",
                arch: "<pivot js_class='contract_employee_report_pivot'/>",
                mockRPC: async (route, args) => {
                    const { method, model } = args;
                    if (method === "search_read") {
                        assert.step(method);
                        assert.strictEqual(model, "hr.contract.employee.report");
                        return [{ id: 1 }, { id: 2 }];
                    }
                },
            });
            const doAction = graph.env.services.action.doAction;
            patchWithCleanup(graph.env.services.action, {
                doAction: (actionRequest, options) => {
                    const { domain, res_model, views } = actionRequest;
                    if (res_model) {
                        assert.step(`doAction ${res_model}`);
                        assert.deepEqual(domain, [["id", "in", [1, 2]]]);
                        assert.deepEqual(views, [
                            [false, "list"],
                            [false, "form"],
                        ]);
                        return;
                    }
                    doAction(actionRequest, options);
                },
            });
            await click(target, ".o_value");
            assert.verifySteps(["search_read", "doAction hr.contract"]);
        }
    );

});
