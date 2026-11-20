import { Component, proxy, xml } from "@odoo/owl";

import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { WebClientOfflinePlugin } from "@web/webclient/offline/webclient_offline_plugin";

import { animationFrame, expect, runAllTimers, test, tick } from "@odoo/hoot";
import {
    contains,
    getService,
    makeTestApp,
    mockOffline,
    mountWithCleanup,
    mountWithSearch,
    onRpc,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { SearchBar } from "@web/search/search_bar/search_bar";
import { defineSearchBarModels } from "../search/search_bar_menu/models";

defineSearchBarModels();

test("offlineUI: disable interactive elements except [data-available-offline]", async () => {
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="button_to_disable"> Disable this button </button>
                <button type="button" class="button_available_offline" data-available-offline=""> Don't disable this button </button>
            </div>
        `;
    }

    await mountWithCleanup(Root);
    expect(`.button_to_disable`).not.toHaveAttribute("disabled");
    expect(`.button_available_offline`).not.toHaveAttribute("disabled");

    getService(OfflinePlugin).setOffline(true);
    expect(`.button_to_disable`).toHaveAttribute("disabled");
    expect(`.button_available_offline`).not.toHaveAttribute("disabled");
    expect(`.button_to_disable`).toHaveClass("o_disabled_offline");
    expect(`.button_available_offline`).not.toHaveClass("o_disabled_offline");

    getService(OfflinePlugin).setOffline(false);
    expect(`.button_to_disable`).not.toHaveAttribute("disabled");
    expect(`.button_available_offline`).not.toHaveAttribute("disabled");
});

test("offlineUI: don't disable already disabled elements", async () => {
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="button" disabled="disabled"> Disabled button </button>
                <input type="checkbox" class="checkbox" disabled="disabled"/>
            </div>
        `;
    }

    await mountWithCleanup(Root);
    expect(`.button`).toHaveAttribute("disabled");
    expect(`.checkbox`).toHaveAttribute("disabled");

    getService(OfflinePlugin).setOffline(true);
    expect(`.button`).toHaveAttribute("disabled");
    expect(`.checkbox`).toHaveAttribute("disabled");
    expect(`.button`).not.toHaveClass("o_disabled_offline");
    expect(`.checkbox`).not.toHaveClass("o_disabled_offline");

    getService(OfflinePlugin).setOffline(false);
    expect(`.button`).toHaveAttribute("disabled");
    expect(`.checkbox`).toHaveAttribute("disabled");
});

test("offlineUI: react to [data-available-offline] attribute changes", async () => {
    let state;
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="btn1" t-att="{ 'data-available-offline': this.state.btn1Available }">
                    First
                </button>
                <button type="button" class="btn2" t-att="{ 'data-available-offline': this.state.btn2Available }">
                    Second
                </button>
            </div>
        `;

        setup() {
            this.state = proxy({
                btn1Available: true,
                btn2Available: false,
            });
            state = this.state;
        }
    }

    await mountWithCleanup(Root);
    expect(".btn1").not.toHaveAttribute("disabled");
    expect(".btn2").not.toHaveAttribute("disabled");

    getService(OfflinePlugin).setOffline(true);
    expect(".btn1").not.toHaveAttribute("disabled");
    expect(".btn2").toHaveAttribute("disabled");

    state.btn1Available = false;
    state.btn2Available = true;
    await animationFrame();
    expect(".btn1").toHaveAttribute("disabled");
    expect(".btn2").not.toHaveAttribute("disabled");
});

test("isAvailableOffline", async () => {
    await makeTestApp();
    expect(getService(WebClientOfflinePlugin).isOffline()).toBe(false);

    await getService(WebClientOfflinePlugin).setAvailableOffline(1, "list", { search: { key: 1 } });
    await getService(WebClientOfflinePlugin).setAvailableOffline(1, "form", { resId: 1 });

    // go offline
    getService(OfflinePlugin).setOffline(true);
    await getService(WebClientOfflinePlugin).getVisitedStatus();
    expect(getService(WebClientOfflinePlugin).isOffline()).toBe(true);

    expect(getService(WebClientOfflinePlugin).isAvailableOffline(1)).toBe(true);
    expect(getService(WebClientOfflinePlugin).isAvailableOffline(4)).toBe(false);

    expect(getService(WebClientOfflinePlugin).isAvailableOffline(1, "list")).toBe(true);
    expect(getService(WebClientOfflinePlugin).isAvailableOffline(1, "kanban")).toBe(false);

    expect(getService(WebClientOfflinePlugin).isAvailableOffline(1, "list", 1)).toBe(true);
    expect(getService(WebClientOfflinePlugin).isAvailableOffline(1, "kanban", 3)).toBe(false);
});

test("getAvailableSearches", async () => {
    await makeTestApp();
    const offline = getService(WebClientOfflinePlugin);
    expect(offline.isOffline()).toBe(false);

    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "2" } });
    await offline.setAvailableOffline(1, "kanban", { search: { key: "oui" } });
    await offline.setAvailableOffline(2, "kanban", { search: { key: "8" } });

    // go offline
    getService(OfflinePlugin).setOffline(true);
    await tick();
    expect(offline.isOffline()).toBe(true);

    expect(await offline.getAvailableSearches(1, "list")).toEqual([{ key: "2" }, { key: "1" }]);
    expect(await offline.getAvailableSearches(1, "kanban")).toEqual([{ key: "oui" }]);
    expect(await offline.getAvailableSearches(2, "kanban")).toEqual([{ key: "8" }]);
});

test("getAvailableSearches (searches order)", async () => {
    await makeTestApp();
    const offline = getService(WebClientOfflinePlugin);
    expect(offline.isOffline()).toBe(false);

    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "2" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "2" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "3" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "4" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "3" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "5" } });

    // go offline
    getService(OfflinePlugin).setOffline(true);
    await tick();
    expect(offline.isOffline()).toBe(true);

    expect(await offline.getAvailableSearches(1, "list")).toEqual([
        { key: "1" }, // accessed 3 times
        { key: "3" }, // accessed twice
        { key: "2" }, // accessed twice (less recently)
        { key: "5" }, // accessed once
        { key: "4" }, // accessed once (less recently)
    ]);
});

test("relative date filter available offline, loosing its navigation capabilities", async () => {
    const searchBar = await mountWithSearch(SearchBar, {
        resModel: "foo",
        searchViewId: false,
        searchMenuTypes: ["filter"],
        searchViewArch: `
            <search>
                <filter string="Date" name="date_field" date="date_field"/>
            </search>
        `,
    });
    const searchModel = searchBar.env.searchModel;
    await toggleSearchBarMenu();
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "This Week");

    const thisWeekDomain = [
        "&",
        ["date_field", ">=", "today =week_start"],
        ["date_field", "<", "today =week_start +1w"],
    ];
    expect(searchModel.domain).toEqual(thisWeekDomain);
    expect(searchModel.facets.map((f) => f.type)).toEqual(["relative"]);
    expect(`.o_searchview_facet .o_date_nav_btn`).toHaveCount(2);

    const offline = getService(WebClientOfflinePlugin);
    await offline.setAvailableOffline(1, "list", { search: searchModel.getCurrentSearch() });

    await contains(`.o_searchview_facet [aria-label="Next period"]`).click();
    const nextWeekDomain = [
        "&",
        ["date_field", ">=", "today =week_start +1w"],
        ["date_field", "<", "today =week_start +2w"],
    ];
    expect(searchModel.domain).toEqual(nextWeekDomain);
    await offline.setAvailableOffline(1, "list", { search: searchModel.getCurrentSearch() });

    // Go offline: both cached states remain available.
    getService(OfflinePlugin).setOffline(true);
    await tick();
    expect(offline.isOffline()).toBe(true);

    const cachedSearches = await offline.getAvailableSearches(1, "list");
    expect(cachedSearches.length).toBe(2);

    // Both restore their frozen smart-date domain, each degraded to a plain
    // static "filter" facet (no navigation arrows). getAvailableSearches returns
    // the most recently cached first, so "Next week" precedes "This Week".
    searchModel.applySearch(cachedSearches[0]);
    await animationFrame();
    expect(searchModel.domain).toEqual(nextWeekDomain);
    expect(searchModel.facets.map((f) => f.type)).toEqual(["filter"]);
    expect(`.o_searchview_facet .o_date_nav_btn`).toHaveCount(0);

    searchModel.applySearch(cachedSearches[1]);
    await animationFrame();
    expect(searchModel.domain).toEqual(thisWeekDomain);
    expect(searchModel.facets.map((f) => f.type)).toEqual(["filter"]);
    expect(`.o_searchview_facet .o_date_nav_btn`).toHaveCount(0);
});

test("scheduleORM", async () => {
    onRpc("partner", "modify", ({ model, method, args, kwargs }) => {
        expect.step({ model, method, args, kwargs: JSON.stringify(kwargs) });
    });
    await makeTestApp();
    const offline = getService(WebClientOfflinePlugin);
    expect(offline.isOffline()).toBe(false);

    // go offline
    getService(OfflinePlugin).setOffline(true);
    await tick();
    expect(offline.isOffline()).toBe(true);

    await offline.scheduleORM("partner", "create", [22, 13], { arg1: true, arg2: false }, {});
    await offline.scheduleORM(
        "partner",
        "modify",
        [22, 13],
        { arg3: true },
        { id: 22, extras: { toSaveMore: true } }
    );

    expect(offline.hasScheduledCalls).toBe(true);
    expect(offline._ormToSync()).toEqual({
        22: {
            key: 22,
            value: {
                args: [22, 13],
                extras: {
                    toSaveMore: true,
                },
                kwargs: {
                    arg3: true,
                },
                method: "modify",
                model: "partner",
            },
        },
        "7b1d3bb0": {
            key: "7b1d3bb0",
            value: {
                args: [22, 13],
                extras: undefined,
                kwargs: {
                    arg1: true,
                    arg2: false,
                },
                method: "create",
                model: "partner",
            },
        },
    });

    offline.removeScheduledORM("7b1d3bb0");
    expect(offline._ormToSync()).toEqual({
        22: {
            key: 22,
            value: {
                args: [22, 13],
                extras: {
                    toSaveMore: true,
                },
                kwargs: {
                    arg3: true,
                },
                method: "modify",
                model: "partner",
            },
        },
    });

    // go online
    getService(OfflinePlugin).setOffline(false);
    await tick();
    expect(offline.isOffline()).toBe(false);

    //SyncORM !
    await expect.waitForSteps([
        {
            args: [22, 13],
            kwargs: '{"arg3":true,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}}',
            method: "modify",
            model: "partner",
        },
    ]);
});

test("syncORM ConnectionLost", async () => {
    // If a ConnectionLost is detected when syncing,
    // we should stop the syncing and don't put the scheduledORM as in error.
    const setOffline = mockOffline();
    const def = Promise.withResolvers();

    onRpc("partner", "create", async () => {
        await def.promise;
        expect.step("partner create was called: returned connection lost");
        return new Response("", { status: 502 });
    });

    onRpc("partner", "modify", () => {
        throw Error("This shouldn't be called");
    });

    await makeTestApp();
    expect(getService(WebClientOfflinePlugin).isOffline()).toBe(false);

    // go offline
    await setOffline(true);
    expect(getService(WebClientOfflinePlugin).isOffline()).toBe(true);

    await getService(WebClientOfflinePlugin).scheduleORM(
        "partner",
        "create",
        [22, 13],
        { arg1: true, arg2: false },
        { extras: { timeStamp: 11 } }
    );
    await getService(WebClientOfflinePlugin).scheduleORM(
        "partner",
        "modify",
        [22, 13],
        { arg3: true },
        { id: 22, extras: { timeStamp: 22, toSaveMore: true } }
    );

    // go online
    await setOffline(false);
    expect(getService(WebClientOfflinePlugin).isOffline()).toBe(false);

    expect(getService(WebClientOfflinePlugin).syncingORM()).toBe(true);

    //go offline Again
    await setOffline(true);
    def.resolve();
    await tick();
    await runAllTimers(); // run the time for the rpc to sync

    // SyncORM !
    // Only the first should be try to be sync, as we go offline in the middle of the first sync
    await expect.waitForSteps(["partner create was called: returned connection lost"]);

    expect(getService(WebClientOfflinePlugin).syncingORM()).toBe(false);

    // Neither of the scheduledORM should be in error !
    expect(getService(WebClientOfflinePlugin)._ormToSync()).toEqual({
        22: {
            key: "22",
            value: {
                args: [22, 13],
                extras: {
                    toSaveMore: true,
                    timeStamp: 22,
                },
                kwargs: {
                    arg3: true,
                },
                method: "modify",
                model: "partner",
            },
        },
        ba559cc9: {
            key: "ba559cc9",
            value: {
                args: [22, 13],
                extras: {
                    timeStamp: 11,
                },
                kwargs: {
                    arg1: true,
                    arg2: false,
                },
                method: "create",
                model: "partner",
            },
        },
    });
});
