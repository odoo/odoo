import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineSpreadsheetDashboardModels,
    getServerData,
} from "@spreadsheet_dashboard/../tests/helpers/data";
import { createDashboardLoader } from "../helpers/dashboard_action";
import { rpcBus } from "@web/core/network/rpc";

defineSpreadsheetDashboardModels();

async function createSearchModel(params = {}) {
    const loader = params.loader || (await createDashboardLoader(params));
    loader.load();
    await animationFrame();
    const dashboard = loader.getDashboard(params.dashboardId || 1);
    await animationFrame();
    return dashboard.searchModel;
}

test("loads favorites for a dashboard", async () => {
    const searchModel = await createSearchModel({
        mockRPC: function (route, args) {
            if (
                args.method === "get_filters" &&
                args.model === "spreadsheet.dashboard.favorite.filters"
            ) {
                expect.step("get favorite filter");
                return [
                    {
                        id: 10,
                        name: "My Fav",
                        is_default: true,
                        dashboard_id: 1,
                        global_filters: { gf_1: "A", gf_2: 10 },
                    },
                ];
            }
        },
    });

    expect.verifySteps(["get favorite filter"]);
    expect(searchModel.activeFavoriteId).toBe(10);

    const fav = searchModel.favoriteRecordMap[10];
    expect(fav.id).toBe(10);
    expect(fav.description).toBe("My Fav");
});

test("should call get_filters only once per dashboard", async () => {
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (
                args.method === "get_filters" &&
                args.model === "spreadsheet.dashboard.favorite.filters"
            ) {
                expect.step(`favorite filter for dashboard ${args.args[0]}`);
            }
        },
    });
    await loader.load();
    loader.getDashboard(1);
    await animationFrame();
    expect.verifySteps(["favorite filter for dashboard 1"]);
    loader.getDashboard(2);
    await animationFrame();
    expect.verifySteps(["favorite filter for dashboard 2"]);
    loader.getDashboard(1);
    await animationFrame();
    expect.verifySteps([]);
});

test("dashboard cache is invalidated and reloaded on favorite filter RPC updates", async () => {
    const loader = await createDashboardLoader({
        mockRPC: function (route, args) {
            if (
                args.method === "get_filters" &&
                args.model === "spreadsheet.dashboard.favorite.filters"
            ) {
                expect.step(`favorite filter for dashboard ${args.args[0]}`);
            }
        },
    });

    await loader.load();
    loader.getDashboard(1);
    await animationFrame();
    expect.verifySteps(["favorite filter for dashboard 1"]);
    loader.getDashboard(2);
    await animationFrame();
    expect.verifySteps(["favorite filter for dashboard 2"]);

    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "spreadsheet.dashboard.favorite.filters", method: "unlink" } },
        settings: {},
        error: {},
    });
    await animationFrame();
    loader._markDashboardsStale();
    await animationFrame();
    loader.getDashboard(1);
    await animationFrame();
    expect.verifySteps(["favorite filter for dashboard 1"]);
});

test("createFavoriteRecord creates and activates a new favorite", async () => {
    let createPayload = null;
    const globalFilter = {
        id: "1",
        type: "relation",
        label: "Relation Filter",
        modelName: "product",
        defaultValue: { operator: "in", ids: [37] }, // xphone
    };
    const serverData = getServerData({ globalFilters: [globalFilter] });
    const searchModel = await createSearchModel({
        serverData,
        dashboardId: 789,
        mockRPC(route, args) {
            if (args.model === "spreadsheet.dashboard.favorite.filters") {
                if (args.method === "create") {
                    expect.step("create favorite");
                    createPayload = args.args[0][0];
                    return [55];
                }
                if (args.method === "get_filters") {
                    return [];
                }
            }
        },
    });

    const serverId = await searchModel.createFavoriteRecord("NewFav", true, [
        {
            globalFilter,
            value: { operator: "in", ids: [41] }, // xpad
        },
    ]);

    expect.verifySteps(["create favorite"]);
    expect(serverId).toBe(55);
    expect(searchModel.activeFavoriteId).toBe(55);
    expect(createPayload.name).toBe("NewFav");
    expect(createPayload.global_filters).toEqual({ 1: { operator: "in", ids: [41] } });
});

describe("Facet state", () => {
    const spreadsheetData = {
        globalFilters: [
            {
                id: "1",
                type: "relation",
                label: "Relation Filter",
                modelName: "product",
                defaultValue: { operator: "in", ids: [37] }, // xphone
            },
        ],
    };
    const serverData = getServerData(spreadsheetData);

    test("add favorite facet when default favorite is active", async () => {
        const searchModel = await createSearchModel({
            serverData,
            dashboardId: 789,
            mockRPC: function (route, args) {
                if (
                    args.method === "get_filters" &&
                    args.model === "spreadsheet.dashboard.favorite.filters"
                ) {
                    return [
                        {
                            id: 10,
                            name: "Default Fav",
                            is_default: true,
                            dashboard_id: 789,
                            global_filters: {},
                        },
                    ];
                }
            },
        });
        const facet = searchModel.state.facets[0];
        expect(facet.type).toBe("favorite");
        expect(facet.values[0]).toBe("Default Fav");
    });

    test("add field facets when there is not any default favorite", async () => {
        const searchModel = await createSearchModel({
            serverData,
            dashboardId: 789,
            mockRPC: function (route, args) {
                if (
                    args.method === "get_filters" &&
                    args.model === "spreadsheet.dashboard.favorite.filters"
                ) {
                    return [
                        {
                            id: 10,
                            name: "Default Fav",
                            is_default: false,
                            dashboard_id: 789,
                            global_filters: {},
                        },
                    ];
                }
            },
        });
        const facet = searchModel.state.facets[0];
        expect(facet.type).toBe("field");
        expect(facet.values[0]).toBe("xphone");
    });
});

describe("Manual Filter Update", () => {
    const globalFilter = {
        id: "1",
        type: "relation",
        label: "Relation Filter",
        modelName: "product",
    };
    const serverData = getServerData({ globalFilters: [globalFilter] });
    let searchModel;
    beforeEach(async () => {
        searchModel = await createSearchModel({
            dashboardId: 789,
            serverData,
            mockRPC: function (route, args) {
                if (
                    args.method === "get_filters" &&
                    args.model === "spreadsheet.dashboard.favorite.filters"
                ) {
                    return [
                        {
                            id: 10,
                            name: "Default Fav",
                            is_default: true,
                            dashboard_id: 789,
                            global_filters: { 1: { operator: "in", ids: [37] } }, // xphone
                        },
                    ];
                }
            },
        });
    });

    test("deactivates favorite when values change", async () => {
        expect(searchModel.activeFavoriteId).toBe(10);
        searchModel.handleManualFilterConfirm([
            {
                globalFilter,
                value: { operator: "in", ids: [41] }, // xpad
            },
        ]);
        expect(searchModel.activeFavoriteId).toBe(undefined);
    });

    test("does not deactivate favorite when values do not change", async () => {
        expect(searchModel.activeFavoriteId).toBe(10);
        searchModel.handleManualFilterConfirm([
            {
                globalFilter,
                value: { operator: "in", ids: [37] }, // xpad
            },
        ]);
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(10);
    });
});
