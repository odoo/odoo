/** @odoo-module */

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    DashboardLoader,
    Status,
} from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_loader";
import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { getDashboardServerData } from "../utils/data";

import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";
import { getCellValue } from "@spreadsheet/../tests/utils/getters";
import { RPCError } from "@web/core/network/rpc_service";

/**
 * @param {object} [params]
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @returns {Promise<DashboardLoader>}
 */
async function createDashboardLoader(params = {}) {
    registry.category("services").add("orm", ormService);
    const env = await makeTestEnv({
        serverData: params.serverData || getDashboardServerData(),
        mockRPC: params.mockRPC,
    });
    return new DashboardLoader(env, env.services.orm, async (dashboardId) => {
        const [record] = await env.services.orm.read(
            "spreadsheet.dashboard",
            [dashboardId],
            ["spreadsheet_data"]
        );
        return { data: JSON.parse(record.spreadsheet_data), revisions: [] };
    });
}

QUnit.module("spreadsheet_dashboard > Dashboard loader");

QUnit.test("load all dashboards of all containers", async (assert) => {
    const loader = await createDashboardLoader();
    loader.load();
    assert.deepEqual(loader.getDashboardGroups(), []);
    await nextTick();
    assert.deepEqual(loader.getDashboardGroups(), [
        {
            id: 1,
            name: "Container 1",
            dashboards: [
                {
                    id: 1,
                    displayName: "Dashboard CRM 1",
                    status: Status.NotLoaded,
                },
                {
                    id: 2,
                    displayName: "Dashboard CRM 2",
                    status: Status.NotLoaded,
                },
            ],
        },
        {
            id: 2,
            name: "Container 2",
            dashboards: [
                {
                    id: 3,
                    displayName: "Dashboard Accounting 1",
                    status: Status.NotLoaded,
                },
            ],
        },
    ]);
});

QUnit.test("load twice does not duplicate spreadsheets", async (assert) => {
    const loader = await createDashboardLoader();
    await loader.load();
    assert.deepEqual(loader.getDashboardGroups()[1].dashboards, [
        { id: 3, displayName: "Dashboard Accounting 1", status: Status.NotLoaded },
    ]);
    await loader.load();
    assert.deepEqual(loader.getDashboardGroups()[1].dashboards, [
        { id: 3, displayName: "Dashboard Accounting 1", status: Status.NotLoaded },
    ]);
});

QUnit.test("load spreadsheet data", async (assert) => {
    const loader = await createDashboardLoader();
    await loader.load();
    const result = loader.getDashboard(3);
    assert.strictEqual(result.status, Status.Loading);
    await nextTick();
    assert.strictEqual(result.status, Status.Loaded);
    assert.ok(result.model);
});

QUnit.test("load spreadsheet data only once", async (assert) => {
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (args.model === "spreadsheet.dashboard" && args.method === "read") {
                // read names
                assert.step(`spreadsheet ${args.args[0]} loaded`);
            }
            if (
                args.model === "spreadsheet.dashboard" &&
                args.method === "get_readonly_dashboard"
            ) {
                assert.step(`spreadsheet ${args.args[0]} loaded`);
            }
        },
    });
    await loader.load();
    let result = loader.getDashboard(3);
    await nextTick();
    assert.strictEqual(result.status, Status.Loaded);
    assert.verifySteps(["spreadsheet 3 loaded"]);
    result = loader.getDashboard(3);
    await nextTick();
    assert.strictEqual(result.status, Status.Loaded);
    assert.verifySteps([]);
});

QUnit.test("don't return empty dashboard group", async (assert) => {
    const loader = await createDashboardLoader({
        mockRPC: async function (route, args) {
            if (args.method === "web_search_read" && args.model === "spreadsheet.dashboard.group") {
                return {
                    length: 2,
                    records: [
                        {
                            id: 45,
                            name: "Group A",
                            dashboard_ids: [{ id: 1, name: "Dashboard CRM 1" }],
                        },
                        {
                            id: 46,
                            name: "Group B",
                            dashboard_ids: [],
                        },
                    ],
                };
            }
        },
    });
    await loader.load();
    assert.deepEqual(loader.getDashboardGroups(), [
        {
            id: 45,
            name: "Group A",
            dashboards: [
                {
                    id: 1,
                    displayName: "Dashboard CRM 1",
                    status: Status.NotLoaded,
                },
            ],
        },
    ]);
});

QUnit.test("load multiple spreadsheets", async (assert) => {
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (args.method === "web_search_read" && args.model === "spreadsheet.dashboard.group") {
                assert.step("load groups");
            }
            if (args.method === "read" && args.model === "spreadsheet.dashboard") {
                // read names
                assert.step(`spreadsheet ${args.args[0]} loaded`);
            }
            if (
                args.model === "spreadsheet.dashboard" &&
                args.method === "get_readonly_dashboard"
            ) {
                assert.step(`spreadsheet ${args.args[0]} loaded`);
            }
        },
    });
    await loader.load();
    assert.verifySteps(["load groups"]);
    loader.getDashboard(1);
    await nextTick();
    assert.verifySteps(["spreadsheet 1 loaded"]);
    loader.getDashboard(2);
    await nextTick();
    assert.verifySteps(["spreadsheet 2 loaded"]);
    loader.getDashboard(1);
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("load spreadsheet data with error", async (assert) => {
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (
                args.method === "get_readonly_dashboard" &&
                args.model === "spreadsheet.dashboard"
            ) {
                const error = new RPCError();
                error.data = { message: "Bip" };
                throw error;
            }
        },
    });
    await loader.load();
    const result = loader.getDashboard(3);
    assert.strictEqual(result.status, Status.Loading);
    await result.promise.catch(() => assert.step("error"));
    assert.strictEqual(result.status, Status.Error);
    assert.strictEqual(result.error.data.message, "Bip");
    assert.verifySteps(["error"], "error is thrown");
});

QUnit.test("async formulas are correctly evaluated", async (assert) => {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: { content: `=ODOO.CURRENCY.RATE("EUR","USD")` }, // an async formula
                },
            },
        ],
    };
    const serverData = getDashboardServerData();
    const dashboardId = 15;
    serverData.models["spreadsheet.dashboard"].records = [
        {
            id: dashboardId,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            json_data: JSON.stringify(spreadsheetData),
            name: "Dashboard Accounting 1",
            dashboard_group_id: 2,
        },
    ];
    serverData.models["spreadsheet.dashboard.group"].records = [
        { id: 1, name: "Container 1", dashboard_ids: [dashboardId] },
    ];
    const loader = await createDashboardLoader({
        serverData,
        mockRPC: function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const info = args.args[0][0];
                return [{ ...info, rate: 0.9 }];
            }
        },
    });
    await loader.load();
    loader.getDashboard(dashboardId);
    await nextTick();
    const { model } = loader.getDashboard(dashboardId);
    await waitForDataSourcesLoaded(model);
    assert.strictEqual(await getCellValue(model, "A1"), 0.9);
});

QUnit.test("Model is in dashboard mode", async (assert) => {
    const loader = await createDashboardLoader();
    await loader.load();
    loader.getDashboard(3);
    await nextTick();
    const { model } = loader.getDashboard(3);
    assert.strictEqual(model.config.mode, "dashboard");
});

QUnit.test("Model is in dashboard mode", async (assert) => {
    patchWithCleanup(DashboardLoader.prototype, {
        _activateFirstSheet: () => {
            assert.step("activate sheet");
        },
    });
    const loader = await createDashboardLoader();
    await loader.load();
    loader.getDashboard(3);
    await nextTick();
    assert.verifySteps(["activate sheet"]);
});

QUnit.test("default currency format", async (assert) => {
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (
                args.model === "spreadsheet.dashboard" &&
                args.method === "get_readonly_dashboard"
            ) {
                return {
                    data: {},
                    revisions: [],
                    default_currency: {
                        code: "Odoo",
                        symbol: "θ",
                        position: "after",
                        decimalPlaces: 2,
                    },
                };
            }
            if (args.method === "get_company_currency_for_spreadsheet") {
                throw new Error("Should not make any RPC");
            }
        },
    });
    await loader.load();
    const result = loader.getDashboard(3);
    assert.strictEqual(result.status, Status.Loading);
    await nextTick();
    const { model } = loader.getDashboard(3);
    assert.strictEqual(model.getters.getCompanyCurrencyFormat(), "#,##0.00[$θ]");
});
