import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { getCellValue } from "@spreadsheet/../tests/helpers/getters";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import {
    defineSpreadsheetDashboardModels,
    getDashboardServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import {
    DashboardLoader,
    Status,
} from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_loader";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { RPCError } from "@web/core/network/rpc";

defineSpreadsheetDashboardModels();

/**
 * @param {object} [params]
 * @param {object} [params.serverData]
 * @param {function} [params.mockRPC]
 * @returns {Promise<DashboardLoader>}
 */
async function createDashboardLoader(params = {}) {
    const env = await makeSpreadsheetMockEnv({
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

test("load all dashboards of all containers", async () => {
    const loader = await createDashboardLoader();
    loader.load();
    expect(loader.getDashboardGroups()).toEqual([]);
    await animationFrame();
    expect(loader.getDashboardGroups()).toEqual([
        {
            id: 1,
            name: "Container 1",
            dashboards: [
                {
                    data: {
                        id: 1,
                        name: "Dashboard CRM 1",
                        is_favorite: false,
                    },
                    status: Status.NotLoaded,
                },
                {
                    data: {
                        id: 2,
                        name: "Dashboard CRM 2",
                        is_favorite: false,
                    },
                    status: Status.NotLoaded,
                },
            ],
        },
        {
            id: 2,
            name: "Container 2",
            dashboards: [
                {
                    data: {
                        id: 3,
                        name: "Dashboard Accounting 1",
                        is_favorite: false,
                    },
                    status: Status.NotLoaded,
                },
            ],
        },
    ]);
});

test("load twice does not duplicate spreadsheets", async () => {
    const loader = await createDashboardLoader();
    await loader.load();
    expect(loader.getDashboardGroups()[1].dashboards).toMatchObject([{ status: Status.NotLoaded }]);
    await loader.load();
    expect(loader.getDashboardGroups()[1].dashboards).toMatchObject([{ status: Status.NotLoaded }]);
});

test("load spreadsheet data", async () => {
    const loader = await createDashboardLoader();
    await loader.load();
    const result = loader.getDashboard(3);
    expect(result.status).toBe(Status.Loading);
    await animationFrame();
    expect(result.status).toBe(Status.Loaded);
    expect(result.model).not.toBe(undefined);
});

test("load spreadsheet data only once", async () => {
    onRpc("/spreadsheet/dashboard/data/3", () => expect.step("spreadsheet 3 loaded"));
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (args.model === "spreadsheet.dashboard" && args.method === "read") {
                // read names
                expect.step(`spreadsheet ${args.args[0]} loaded`);
            }
        },
    });
    await loader.load();
    let result = loader.getDashboard(3);
    await animationFrame();
    expect(result.status).toBe(Status.Loaded);
    expect.verifySteps(["spreadsheet 3 loaded"]);
    result = loader.getDashboard(3);
    await animationFrame();
    expect(result.status).toBe(Status.Loaded);
    expect.verifySteps([]);
});

test("don't return empty dashboard group", async () => {
    const loader = await createDashboardLoader({
        mockRPC: async function (route, args) {
            if (args.method === "web_search_read" && args.model === "spreadsheet.dashboard.group") {
                return {
                    length: 2,
                    records: [
                        {
                            id: 45,
                            name: "Group A",
                            published_dashboard_ids: [{ id: 1, name: "Dashboard CRM 1" }],
                        },
                        {
                            id: 46,
                            name: "Group B",
                            published_dashboard_ids: [],
                        },
                    ],
                };
            }
        },
    });
    await loader.load();
    expect(loader.getDashboardGroups()).toEqual([
        {
            id: 45,
            name: "Group A",
            dashboards: [
                {
                    data: { id: 1, name: "Dashboard CRM 1" },
                    status: Status.NotLoaded,
                },
            ],
        },
    ]);
});

test("load multiple spreadsheets", async () => {
    onRpc("/spreadsheet/dashboard/data/1", () => expect.step("spreadsheet 1 loaded"));
    onRpc("/spreadsheet/dashboard/data/2", () => expect.step("spreadsheet 2 loaded"));
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (args.method === "web_search_read" && args.model === "spreadsheet.dashboard.group") {
                expect.step("load groups");
            }
            if (args.method === "read" && args.model === "spreadsheet.dashboard") {
                // read names
                expect.step(`spreadsheet ${args.args[0]} loaded`);
            }
        },
    });
    await loader.load();
    expect.verifySteps(["load groups"]);
    loader.getDashboard(1);
    await animationFrame();
    expect.verifySteps(["spreadsheet 1 loaded"]);
    loader.getDashboard(2);
    await animationFrame();
    expect.verifySteps(["spreadsheet 2 loaded"]);
    loader.getDashboard(1);
    await animationFrame();
    expect.verifySteps([]);
});

test("load spreadsheet data with error", async () => {
    onRpc(
        "/spreadsheet/dashboard/data/*",
        () => {
            const error = new RPCError();
            error.data = { message: "Bip" };
            throw error;
        },
        { pure: true }
    );
    const loader = await createDashboardLoader();
    await loader.load();
    const result = loader.getDashboard(3);
    expect(result.status).toBe(Status.Loading);
    await result.promise.catch(() => expect.step("error"));
    expect(result.status).toBe(Status.Error);
    expect(result.error.data.message).toBe("Bip");
    // error is thrown
    expect.verifySteps(["error"]);
});

test("async formulas are correctly evaluated", async () => {
    const spreadsheetData = {
        sheets: [
            {
                id: "sheet1",
                cells: {
                    A1: '=ODOO.CURRENCY.RATE("EUR","USD")', // an async formula
                },
            },
        ],
    };
    const serverData = getDashboardServerData();
    const dashboardId = 15;
    serverData.models["spreadsheet.dashboard.group"].records = [
        { id: 1, name: "Container 1", published_dashboard_ids: [dashboardId] },
    ];
    serverData.models["spreadsheet.dashboard"].records = [
        {
            id: dashboardId,
            spreadsheet_data: JSON.stringify(spreadsheetData),
            json_data: JSON.stringify(spreadsheetData),
            name: "Dashboard Accounting 1",
            dashboard_group_id: 1,
        },
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
    await animationFrame();
    const { model } = loader.getDashboard(dashboardId);
    await waitForDataLoaded(model);
    expect(await getCellValue(model, "A1")).toBe(0.9);
});

test("Model is in dashboard mode", async () => {
    const loader = await createDashboardLoader();
    await loader.load();
    loader.getDashboard(3);
    await animationFrame();
    const { model } = loader.getDashboard(3);
    expect(model.config.mode).toBe("dashboard");
});

test("Model is in dashboard mode [2]", async () => {
    patchWithCleanup(DashboardLoader.prototype, {
        _activateFirstSheet: () => {
            expect.step("activate sheet");
        },
    });
    const loader = await createDashboardLoader();
    await loader.load();
    loader.getDashboard(3);
    await animationFrame();
    expect.verifySteps(["activate sheet"]);
});

test("default currency format", async () => {
    onRpc(
        "/spreadsheet/dashboard/data/*",
        () => ({
            data: {},
            revisions: [],
            default_currency: {
                code: "Odoo",
                symbol: "θ",
                position: "after",
                decimalPlaces: 2,
            },
        }),
        { pure: true }
    );
    const loader = await createDashboardLoader();
    await loader.load();
    const result = loader.getDashboard(3);
    expect(result.status).toBe(Status.Loading);
    await animationFrame();
    const { model } = loader.getDashboard(3);
    expect(model.getters.getCompanyCurrencyFormat()).toBe("#,##0.00[$θ]");
});
