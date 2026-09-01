import { beforeEach, expect, queryAllAttributes, queryAllTexts, test } from "@odoo/hoot";
import {
    contains,
    defineMenus,
    getService,
    makeTestApp,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { AppsSidebar } from "@web/webclient/apps_sidebar/apps_sidebar";
import {
    getAppsSidebarState,
    toggleAppsSidebar,
} from "@web/webclient/apps_sidebar/apps_sidebar_state";

beforeEach(() => {
    defineMenus([
        { id: 1, name: "App1", xmlid: "menu_1", actionID: 1001 },
        { id: 2, name: "App2", xmlid: "menu_2", actionID: 1002 },
    ]);
});

test.tags("desktop");
test("not displayed by default", async () => {
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar").toHaveCount(0);
});

test.tags("desktop");
test("displays an entry per app once enabled", async () => {
    toggleAppsSidebar();
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar").toHaveCount(1);
    expect(queryAllAttributes(".o_apps_sidebar_app", "data-menu-xmlid")).toEqual([
        "menu_1",
        "menu_2",
    ]);
    expect(queryAllAttributes(".o_apps_sidebar_app", "href")).toEqual([
        "/odoo/action-1001",
        "/odoo/action-1002",
    ]);
    // when collapsed, app names are only available as a tooltip
    expect(queryAllAttributes(".o_apps_sidebar_app", "data-tooltip")).toEqual(["App1", "App2"]);
});

test.tags("desktop");
test("highlights the current app", async () => {
    toggleAppsSidebar();
    await makeTestApp();
    getService("menu").setCurrentMenu(2);
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar_app_active").toHaveCount(1);
    expect(".o_apps_sidebar_app_active").toHaveAttribute("data-menu-xmlid", "menu_2");
});

test.tags("desktop");
test("clicking on an app selects it", async () => {
    toggleAppsSidebar();
    await makeTestApp();
    patchWithCleanup(getService("menu"), {
        selectMenu(menu) {
            expect.step(`selectMenu ${menu.xmlid}`);
        },
    });
    await mountWithCleanup(AppsSidebar);
    await contains(".o_apps_sidebar_app:eq(1)").click();
    expect.verifySteps(["selectMenu menu_2"]);
});

test.tags("desktop");
test("can be expanded and collapsed", async () => {
    toggleAppsSidebar();
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar").not.toHaveClass("o_apps_sidebar_expanded");

    await contains(".o_apps_sidebar_toggle").click();
    expect(".o_apps_sidebar").toHaveClass("o_apps_sidebar_expanded");
    // when expanded, app names are displayed, so they aren't in a tooltip
    expect(queryAllTexts(".o_apps_sidebar_app")).toEqual(["App1", "App2"]);
    expect(queryAllAttributes(".o_apps_sidebar_app", "data-tooltip")).toEqual([null, null]);

    await contains(".o_apps_sidebar_toggle").click();
    expect(".o_apps_sidebar").not.toHaveClass("o_apps_sidebar_expanded");
    expect(queryAllTexts(".o_apps_sidebar_app")).toEqual(["", ""]);
});

test.tags("desktop");
test("only displays pinned apps, if any", async () => {
    toggleAppsSidebar();
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar_app").toHaveCount(2);

    // pin the second app
    await contains(".o_apps_sidebar_footer .dropdown-toggle").click();
    expect(queryAllTexts(".o_apps_sidebar_pin_item")).toEqual(["App1", "App2"]);
    await contains(".o_apps_sidebar_pin_item:eq(1)").click();
    expect(".o_apps_sidebar_app").toHaveCount(1);
    expect(".o_apps_sidebar_app").toHaveAttribute("data-menu-xmlid", "menu_2");
    // the menu stays open, s.t. several apps can be (un)pinned at once
    expect(".o_apps_sidebar_pin_menu").toHaveCount(1);

    // unpin it: all apps are displayed again
    await contains(".o_apps_sidebar_pin_item:eq(1)").click();
    expect(".o_apps_sidebar_app").toHaveCount(2);
});

test.tags("desktop");
test("state is kept in the local storage", async () => {
    const key = `web.apps_sidebar.${user.userId}`;
    toggleAppsSidebar();
    await mountWithCleanup(AppsSidebar);
    await contains(".o_apps_sidebar_toggle").click();
    await contains(".o_apps_sidebar_footer .dropdown-toggle").click();
    await contains(".o_apps_sidebar_pin_item:eq(0)").click();

    expect(JSON.parse(browser.localStorage.getItem(key))).toEqual({
        isVisible: true,
        isExpanded: true,
        pinnedApps: ["menu_1"],
    });
});

test.tags("desktop");
test("corrupted local storage state falls back on the default one", async () => {
    browser.localStorage.setItem(`web.apps_sidebar.${user.userId}`, "}not json{");
    expect(getAppsSidebarState()).toEqual({
        isVisible: false,
        isExpanded: false,
        pinnedApps: [],
    });
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar").toHaveCount(0);
});

test.tags("mobile");
test("not displayed on small screens", async () => {
    toggleAppsSidebar();
    await mountWithCleanup(AppsSidebar);
    expect(".o_apps_sidebar").toHaveCount(0);
});
