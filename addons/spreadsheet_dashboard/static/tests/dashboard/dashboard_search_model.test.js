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
        mockRPC: function (_, args) {
            if (
                args.method === "search_read" &&
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
    let callCount = 0;
    const loader = await createDashboardLoader({
        mockRPC: function (_, args) {
            if (
                args.method === "search_read" &&
                args.model === "spreadsheet.dashboard.favorite.filters"
            ) {
                callCount++;
            }
        },
    });
    loader.getDashboard(1);
    await animationFrame();
    loader.getDashboard(2);
    await animationFrame();
    loader.getDashboard(1);
    await animationFrame();
    expect(callCount).toBe(2);
});

test("dashboard cache is invalidated and reloaded on favorite filter RPC updates", async () => {
    const loader = await createDashboardLoader({
        mockRPC: function (_, args) {
            if (
                args.method === "search_read" &&
                args.model === "spreadsheet.dashboard.favorite.filters"
            ) {
                const domain = args.kwargs?.domain || [];
                const dashboardId = domain.find(
                    ([field, operator]) => field === "dashboard_id" && operator === "="
                )?.[2];
                expect.step(`favorite filter for dashboard ${dashboardId}`);
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
            mockRPC: function (_, args) {
                if (
                    args.method === "search_read" &&
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
            mockRPC: function (_, args) {
                if (
                    args.method === "search_read" &&
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

    test("refresh facets when SET_MANY_GLOBAL_FILTER_VALUE is dispatched", async () => {
        const searchModel = await createSearchModel({
            serverData,
            dashboardId: 789,
            mockRPC: function (_, args) {
                if (
                    args.method === "search_read" &&
                    args.model === "spreadsheet.dashboard.favorite.filters"
                ) {
                    return [];
                }
            },
        });
        let facet = searchModel.state.facets[0];
        expect(facet.type).toBe("field");
        expect(facet.values[0]).toBe("xphone");

        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: { operator: "in", ids: [41] } }],
        });
        await animationFrame();

        facet = searchModel.state.facets[0];
        expect(facet.type).toBe("field");
        expect(facet.values[0]).toBe("xpad");
    });
});

describe("Favorite as baseline facets", () => {
    let searchModel;
    const globalFilter = {
        id: "1",
        type: "relation",
        label: "Relation Filter",
        modelName: "product",
    };
    beforeEach(async () => {
        searchModel = await createSearchModel({
            dashboardId: 789,
            serverData: getServerData({ globalFilters: [globalFilter] }),
            mockRPC: function (_, args) {
                if (
                    args.method === "search_read" &&
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

    test("shows override facet when a filter value differs from the favorite baseline", async () => {
        expect(searchModel.activeFavoriteId).toBe(10);
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: { operator: "in", ids: [41] } }], // xpad
        });
        await animationFrame();

        expect(searchModel.activeFavoriteId).toBe(10);
        const facets = searchModel.state.facets;
        expect(facets.length).toBe(2);
        expect(facets[0].type).toBe("favorite");
        expect(facets[1].type).toBe("field");
        expect(facets[1].values[0]).toBe("xpad");
    });

    test("shows no override facet when filter value matches the favorite baseline", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: { operator: "in", ids: [37] } }],
        });
        await animationFrame();

        const facets = searchModel.state.facets;
        expect(facets.length).toBe(1);
        expect(facets[0].type).toBe("favorite");
    });

    test("shows cleared facet when a favorite filter is explicitly cleared", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: undefined }],
        });
        await animationFrame();

        const facets = searchModel.state.facets;
        expect(facets.length).toBe(2);
        expect(facets[0].type).toBe("favorite");
        expect(facets[1].type).toBe("field");
        expect(facets[1].values[0]).toBe("(Any value)");
    });

    test("clearFilter on an override reverts the filter to the favorite baseline", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: { operator: "in", ids: [41] } }], // xpad
        });
        await animationFrame();

        searchModel.clearFilter("1");
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(10);

        const value = searchModel.spreadsheetModel.getters.getGlobalFilterValue("1");
        expect(value).toEqual({ operator: "in", ids: [37] }); // xphone
        const facets = searchModel.state.facets;
        expect(facets.length).toBe(1);
        expect(facets[0].type).toBe("favorite");
    });

    test("clearFilter on favorite facet clears baseline filters but preserves overrides", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: { operator: "in", ids: [41] } }], // xpad
        });
        await animationFrame();
        searchModel.clearFilter(10);
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(undefined);

        const value = searchModel.spreadsheetModel.getters.getGlobalFilterValue("1");
        expect(value).toEqual({ operator: "in", ids: [41] });
        const facets = searchModel.state.facets;
        expect(facets.length).toBe(1);
        expect(facets[0].type).toBe("field");
        expect(facets[0].values[0]).toBe("xpad");
    });

    test("clearFilter on favorite facet does not restore (Any value) - cleared filters", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "1", value: undefined }], // xpad
        });
        await animationFrame();

        const facets = searchModel.state.facets;
        expect(facets.length).toBe(2);
        expect(facets[0].type).toBe("favorite");
        expect(facets[1].type).toBe("field");
        expect(facets[1].values[0]).toBe("(Any value)");

        searchModel.clearFilter(10);
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(undefined);
        expect(searchModel.state.facets.length).toBe(0);
    });
});

describe("Date filter with favorite", () => {
    let searchModel;
    const dateFilter = { id: "date_1", type: "date", label: "Date Filter" };
    beforeEach(async () => {
        searchModel = await createSearchModel({
            dashboardId: 789,
            serverData: getServerData({ globalFilters: [dateFilter] }),
            mockRPC: function (_, args) {
                if (
                    args.method === "search_read" &&
                    args.model === "spreadsheet.dashboard.favorite.filters"
                ) {
                    return [
                        {
                            id: 10,
                            name: "Date Fav",
                            is_default: true,
                            dashboard_id: 789,
                            global_filters: { date_1: { type: "year", year: 2024 } },
                        },
                    ];
                }
            },
        });
    });

    test("first date filter never appears as a facet -> date filter UI covers it", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "date_1", value: { type: "year", year: 2025 } }],
        });
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(10);
        expect(searchModel.state.facets.every((f) => f.id !== "date_1")).toBe(true);
    });

    test("clearing the favorite removes the date filter value when it still matches the baseline", async () => {
        expect(searchModel.spreadsheetModel.getters.getGlobalFilterValue("date_1")).toEqual({
            type: "year",
            year: 2024,
        });

        searchModel.clearFilter(10);
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(undefined);
        expect(searchModel.spreadsheetModel.getters.getGlobalFilterValue("date_1")).toBe(undefined);
    });

    test("clearing the favorite preserves a user-overridden date filter value", async () => {
        searchModel.spreadsheetModel.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", {
            filters: [{ filterId: "date_1", value: { type: "year", year: 2025 } }],
        });
        await animationFrame();

        searchModel.clearFilter(10);
        await animationFrame();
        expect(searchModel.activeFavoriteId).toBe(undefined);
        expect(searchModel.spreadsheetModel.getters.getGlobalFilterValue("date_1")).toEqual({
            type: "year",
            year: 2025,
        });
    });
});
