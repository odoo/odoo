// @ts-check

import { beforeEach, destroy, expect, test } from "@odoo/hoot";
import {
    queryAll,
    queryAllAttributes,
    queryAllTexts,
    queryOne,
    resize,
} from "@odoo/hoot-dom";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, onRendered, xml } from "@odoo/owl";
import {
    clearRegistry,
    contains,
    defineMenus,
    getService,
    makeMockEnv,
    mountWebClient,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { NavBar } from "@web/webclient/navbar/navbar";

const systrayRegistry = registry.category("systray");

const waitNavbarAdaptation = () => advanceTime(500);

class MySystrayItem extends Component {
    static props = ["*"];
    static template = xml`<li class="my-item">my item</li>`;
}

beforeEach(async () => {
    systrayRegistry.add("addon.myitem", { Component: MySystrayItem });
    defineMenus([{ id: 1 }]);
    return () => {
        clearRegistry(systrayRegistry);
    };
});

test.tags("desktop");
test("can be rendered", async () => {
    await mountWithCleanup(NavBar);
    expect("a.o_menu_toggle").toHaveCount(1, { message: "1 home menu toggle present" });
    expect("a.o_menu_toggle").toHaveAttribute("href", "/odoo");
    expect(".o_navbar_apps_menu").toHaveCount(0, {
        message: "the apps dropdown is gone: the home menu is the app launcher",
    });
});

test.tags("desktop");
test("the toggle asks the home menu service to toggle", async () => {
    await mountWithCleanup(NavBar);
    patchWithCleanup(getService("home_menu"), {
        toggle: async (show) => {
            expect.step(`toggle ${show}`);
        },
    });
    await contains("a.o_menu_toggle").click();
    expect.verifySteps(["toggle undefined"]);
});

test.tags("desktop");
test("href attribute on home menu apps", async () => {
    defineMenus([{ id: 1, actionID: 339 }]);
    await mountWebClient();
    expect(".o_home_menu .o_app").toHaveAttribute("href", "/odoo/action-339");
});

test.tags("desktop");
test("href attribute with path on home menu apps", async () => {
    defineMenus([{ id: 1, actionID: 339, actionPath: "my-path" }]);
    await mountWebClient();
    expect(".o_home_menu .o_app").toHaveAttribute("href", "/odoo/my-path");
});

test.tags("desktop");
test("many sublevels in app menu items", async () => {
    defineMenus([
        { id: 1, children: [2], name: "My app" },
        { id: 2, children: [3], name: "My menu" },
        { id: 3, children: [4], name: "My submenu 1" },
        { id: 4, children: [5], name: "My submenu 2" },
        { id: 5, children: [6], name: "My submenu 3" },
        { id: 6, children: [7], name: "My submenu 4" },
        { id: 7, children: [8], name: "My submenu 5" },
        { id: 8, children: [9], name: "My submenu 6" },
        { id: 9, name: "My submenu 7" },
    ]);
    await makeMockEnv();
    getService("menu").setCurrentMenu(1);
    await mountWithCleanup(NavBar);
    await contains(".o_menu_sections .o-dropdown").click();
    expect(
        queryAll(".o-dropdown--menu > *").map((el) => ({
            text: el.innerText,
            paddingLeft: el.style.paddingLeft,
            tagName: el.tagName,
        })),
    ).toEqual([
        { text: "My submenu 1", paddingLeft: "20px", tagName: "DIV" },
        { text: "My submenu 2", paddingLeft: "32px", tagName: "DIV" },
        { text: "My submenu 3", paddingLeft: "44px", tagName: "DIV" },
        { text: "My submenu 4", paddingLeft: "56px", tagName: "DIV" },
        { text: "My submenu 5", paddingLeft: "68px", tagName: "DIV" },
        { text: "My submenu 6", paddingLeft: "80px", tagName: "DIV" },
        { text: "My submenu 7", paddingLeft: "92px", tagName: "A" },
    ]);
});

test.tags("desktop");
test("data-menu-xmlid attribute on home menu apps", async () => {
    defineMenus([
        { id: 1, actionID: 339, xmlid: "wowl" },
        { id: 2, actionID: 340 },
    ]);
    await mountWebClient();
    expect(queryAllAttributes(".o_home_menu .o_app", "data-menu-xmlid")).toEqual(
        ["wowl", null],
        {
            message:
                "apps should have the correct data-menu-xmlid attribute (only the first is set)",
        },
    );
});

test.tags("desktop");
test("data-menu-xmlid attribute on section items", async () => {
    defineMenus([
        {
            id: 1,
            children: [
                { id: 3, xmlid: "menu_3" },
                { id: 4, xmlid: "menu_4", children: [{ id: 5, xmlid: "menu_5" }] },
            ],
            xmlid: "wowl",
        },
        { id: 2 },
    ]);
    await mountWithCleanup(NavBar);

    getService("menu").setCurrentMenu(1);
    await animationFrame();
    expect(".o_menu_sections .dropdown-item[data-menu-xmlid=menu_3]").toHaveCount(1);

    expect(
        ".o_menu_sections button.dropdown-toggle[data-menu-xmlid=menu_4]",
    ).toHaveCount(1);

    await contains(".o_menu_sections .dropdown-toggle").click();
    expect(".o-dropdown--menu .dropdown-item[data-menu-xmlid=menu_5]").toHaveCount(1);
});

test.tags("desktop");
test("navbar can display current active app", async () => {
    defineMenus([{ id: 1, name: "My app", actionID: 339 }]);
    await mountWithCleanup(NavBar);
    expect(".o_menu_brand").toHaveCount(0, {
        message:
            "should not show the current active app as the menus service has not loaded an app yet",
    });

    getService("menu").setCurrentMenu(1);
    await animationFrame();
    expect(".o_menu_brand").toHaveText("My app", {
        message: "should show the current active app",
    });
});

test("navbar can display systray items", async () => {
    await mountWithCleanup(NavBar);
    expect("li.my-item").toHaveCount(1);
});

test("a systray item whose isDisplayed throws does not break the navbar", async () => {
    class BrokenItem extends Component {
        static props = ["*"];
        static template = xml`<li class="my-broken-item">broken item</li>`;
    }
    systrayRegistry.add("addon.broken", {
        Component: BrokenItem,
        isDisplayed: () => {
            throw new Error("boom");
        },
    });
    patchWithCleanup(console, {
        error: (message) => expect.step(message),
    });
    await mountWithCleanup(NavBar);
    expect(".o_menu_systray").toHaveCount(1, {
        message: "the navbar still renders",
    });
    expect("li.my-item").toHaveCount(1, {
        message: "the healthy item is still displayed",
    });
    expect("li.my-broken-item").toHaveCount(0, {
        message: "the broken item is treated as not displayed",
    });
    expect.verifySteps([`Error in "isDisplayed" of systray item "addon.broken":`]);
});

test("navbar can display systray items ordered based on their sequence", async () => {
    class MyItem1 extends Component {
        static props = ["*"];
        static template = xml`<li class="my-item-1">my item 1</li>`;
    }

    class MyItem2 extends Component {
        static props = ["*"];
        static template = xml`<li class="my-item-2">my item 2</li>`;
    }

    class MyItem3 extends Component {
        static props = ["*"];
        static template = xml`<li class="my-item-3">my item 3</li>`;
    }

    class MyItem4 extends Component {
        static props = ["*"];
        static template = xml`<li class="my-item-4">my item 4</li>`;
    }

    systrayRegistry.remove("addon.myitem");

    systrayRegistry.add("addon.myitem2", { Component: MyItem2 });
    systrayRegistry.add("addon.myitem1", { Component: MyItem1 }, { sequence: 0 });
    systrayRegistry.add("addon.myitem3", { Component: MyItem3 }, { sequence: 100 });
    systrayRegistry.add("addon.myitem4", { Component: MyItem4 });

    await mountWithCleanup(NavBar);
    expect(".o_menu_systray:eq(0) li").toHaveCount(4, {
        message: "four systray items should be displayed",
    });
    expect(queryAllTexts(".o_menu_systray:eq(0) li")).toEqual([
        "my item 3",
        "my item 4",
        "my item 2",
        "my item 1",
    ]);
});

test("navbar updates after adding a systray item", async () => {
    class MyItem1 extends Component {
        static props = ["*"];
        static template = xml`<li class="my-item-1">my item 1</li>`;
    }

    systrayRegistry.remove("addon.myitem");

    systrayRegistry.add("addon.myitem1", { Component: MyItem1 });

    patchWithCleanup(NavBar.prototype, {
        setup() {
            onRendered(() => {
                if (!systrayRegistry.contains("addon.myitem2")) {
                    class MyItem2 extends Component {
                        static props = ["*"];
                        static template = xml`<li class="my-item-2">my item 2</li>`;
                    }
                    systrayRegistry.add("addon.myitem2", { Component: MyItem2 });
                }
            });
            super.setup();
        },
    });
    await mountWithCleanup(NavBar);
    expect(".o_menu_systray:eq(0) li").toHaveCount(2, {
        message: "2 systray items should be displayed",
    });
});

test.tags("desktop");
test("can adapt with 'more' menu sections behavior", async () => {
    class MyNavbar extends NavBar {
        async adapt() {
            await super.adapt();
            const sectionsCount = this.currentAppSections.length;
            const hiddenSectionsCount = this.currentAppSectionsExtra.length;
            expect.step(
                `adapt -> hide ${hiddenSectionsCount}/${sectionsCount} sections`,
            );
        }
    }
    defineMenus([
        {
            id: 1,
            children: [
                { id: 10 },
                { id: 11 },
                {
                    id: 12,
                    children: [{ id: 120 }, { id: 121 }, { id: 122 }],
                },
            ],
        },
    ]);

    await resize({ width: 1080 });

    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => false });

    getService("menu").setCurrentMenu(1);
    await mountWithCleanup(MyNavbar);

    expect(".o_menu_sections > *:not(.o_menu_sections_more):visible").toHaveCount(3, {
        message: "should have 3 menu sections displayed (that are not the 'more' menu)",
    });
    expect(".o_menu_sections_more").toHaveCount(0);

    await resize({ width: 0 });
    await waitNavbarAdaptation();

    expect(".o_menu_sections").not.toBeVisible({
        message: "no menu section should be displayed",
    });

    await resize({ width: 1366 });
    await waitNavbarAdaptation();

    expect(".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)").toHaveCount(
        3,
        {
            message:
                "should have 3 menu sections displayed (that are not the 'more' menu)",
        },
    );
    expect(".o_menu_sections_more").toHaveCount(0, {
        message: "the 'more' menu should not exist",
    });
    expect.verifySteps([
        "adapt -> hide 0/3 sections",
        "adapt -> hide 3/3 sections",
        "adapt -> hide 0/3 sections",
    ]);
});

test.tags("desktop");
test("'more' menu sections adaptations do not trigger render in some cases", async () => {
    let adaptRunning = false;
    let adaptCount = 0;
    let adaptRenderCount = 0;
    class MyNavbar extends NavBar {
        async adapt() {
            adaptRunning = true;
            adaptCount++;
            await super.adapt();
            adaptRunning = false;
        }
        async render() {
            if (adaptRunning) {
                adaptRenderCount++;
            }
            await super.render(...arguments);
        }
    }

    defineMenus([
        {
            id: 1,
            children: [
                { id: 11, name: "Section with a very long name 1" },
                { id: 12, name: "Section with a very long name 2" },
                { id: 13, name: "Section with a very long name 3" },
            ],
        },
    ]);

    await resize({ width: 600 });

    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => false });

    const navbar = await mountWithCleanup(MyNavbar);

    expect(navbar.currentAppSections).toHaveLength(0, { message: "0 app sub menus" });
    expect(".o_navbar").toHaveRect({ width: 600 });
    expect(adaptCount).toBe(1);
    expect(adaptRenderCount).toBe(0, {
        message:
            "during adapt, render not triggered as the navbar has no app sub menus",
    });

    await resize({ width: 0 });
    await waitNavbarAdaptation();

    expect(".o_navbar").toHaveRect({ width: 0 });
    expect(adaptCount).toBe(2);
    expect(adaptRenderCount).toBe(0, {
        message:
            "during adapt, render not triggered as the navbar has no app sub menus",
    });

    getService("menu").setCurrentMenu(1);
    await animationFrame();

    expect(navbar.currentAppSections).toHaveLength(3, { message: "3 app sub menus" });
    expect(navbar.currentAppSectionsExtra).toHaveLength(3, {
        message: "all app sub menus are inside the more menu",
    });
    expect(adaptCount).toBe(3);
    expect(adaptRenderCount).toBe(1, {
        message:
            "during adapt, render triggered as the navbar does not have enough space for app sub menus",
    });

    await resize({ width: 240 });
    await waitNavbarAdaptation();

    expect(navbar.currentAppSectionsExtra).toHaveLength(3, {
        message: "all app sub menus are inside the more menu",
    });
    expect(adaptCount).toBe(4);
    expect(adaptRenderCount).toBe(1, {
        message:
            "during adapt, render not triggered as the more menu dropdown is STILL the same",
    });

    await resize({ width: 1366 });
    await waitNavbarAdaptation();

    expect(navbar.currentAppSections).toHaveLength(3, {
        message: "still 3 app sub menus",
    });
    expect(navbar.currentAppSectionsExtra).toHaveLength(0, {
        message: "all app sub menus are NO MORE inside the more menu",
    });
    expect(adaptCount).toBe(5);
    expect(adaptRenderCount).toBe(2, {
        message:
            "during adapt, render triggered as the more menu dropdown is NO MORE the same",
    });
});

test.tags("desktop");
test("'more' menu sections follow a menu reload that keeps the overflow count", async () => {
    const SECTIONS = [10, 11, 12, 13, 14, 15];
    const build = (/** @type {string[]} */ names) => {
        const menus = {
            root: { id: "root", name: "root", appID: "root", children: [1] },
            1: {
                id: 1,
                appID: 1,
                name: "App",
                children: SECTIONS,
                actionID: 1001,
                xmlid: "app",
            },
        };
        SECTIONS.forEach((id, i) => {
            menus[id] = {
                id,
                appID: 1,
                name: names[i],
                children: [],
                actionID: 2000 + id,
                xmlid: `sec${id}`,
            };
        });
        return menus;
    };
    const before = ["Aaaaaaaa", "Bbbbbbbb", "Cccccccc", "Dddddddd", "Eeeeeeee", "Ffffffff"]; // prettier-ignore
    const after = ["Aaaaaaaa", "Bbbbbbbb", "Cccccccc", "Wwwwwwww", "Xxxxxxxx", "Yyyyyyyy"]; // prettier-ignore

    let names = before;
    onRpc("/web/webclient/load_menus", () => build(names));

    await resize({ width: 700 });
    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => false });

    const menuService = getService("menu");
    await menuService.reload();
    menuService.setCurrentMenu(1);

    const navbar = await mountWithCleanup(NavBar);
    await waitNavbarAdaptation();
    expect(navbar.currentAppSectionsExtra.map((s) => s.name)).toEqual([
        "Dddddddd",
        "Eeeeeeee",
        "Ffffffff",
    ]);

    names = after;
    await menuService.reload();
    await waitNavbarAdaptation();

    await contains(".o_menu_sections_more button").click();
    expect(queryAllTexts(".o-dropdown--menu > *")).toEqual([
        "Wwwwwwww",
        "Xxxxxxxx",
        "Yyyyyyyy",
    ]);
});

test.tags("desktop");
test("'more' menu sections properly updated on app change", async () => {
    defineMenus([
        {
            id: 1,
            children: [
                { id: 10, name: "Section 10" },
                { id: 11, name: "Section 11" },
                {
                    id: 12,
                    name: "Section 12",
                    children: [
                        { id: 120, name: "Section 120" },
                        { id: 121, name: "Section 121" },
                        { id: 122, name: "Section 122" },
                    ],
                },
            ],
        },
        {
            id: 2,
            children: [
                { id: 20, name: "Section 20" },
                { id: 21, name: "Section 21" },
                {
                    id: 22,
                    name: "Section 22",
                    children: [
                        { id: 220, name: "Section 220" },
                        { id: 221, name: "Section 221" },
                        { id: 222, name: "Section 222" },
                    ],
                },
            ],
        },
    ]);

    await resize({ width: 1080 });

    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => false });

    getService("menu").setCurrentMenu(1);
    await mountWithCleanup(NavBar);

    await resize({ width: 0 });
    await waitNavbarAdaptation();
    expect(".o_menu_sections > *:not(.d-none)").toHaveCount(1, {
        message: "only one menu section should be displayed",
    });
    expect(".o_menu_sections_more:not(.d-none)").toHaveCount(1, {
        message: "the displayed menu section should be the 'more' menu",
    });

    await contains(".o_menu_sections_more .dropdown-toggle").click();
    expect(queryAllTexts(".dropdown-menu > *")).toEqual(
        [
            "Section 10",
            "Section 11",
            "Section 12",
            "Section 120",
            "Section 121",
            "Section 122",
        ],
        { message: "'more' menu should contain first app sections" },
    );
    await contains(".o_menu_sections_more .dropdown-toggle").click();

    getService("menu").setCurrentMenu(2);
    await animationFrame();

    await contains(".o_menu_sections_more .dropdown-toggle").click();
    expect(queryAllTexts(".dropdown-menu > *")).toEqual(
        [
            "Section 20",
            "Section 21",
            "Section 22",
            "Section 220",
            "Section 221",
            "Section 222",
        ],
        { message: "'more' menu should contain second app sections" },
    );
});

test.tags("desktop");
test("'more' menu keeps a valid access key with 9 visible sections", async () => {
    class MyNavbar extends NavBar {
        get currentAppSections() {
            return Array.from({ length: 10 }, (_, i) => ({
                id: 100 + i,
                appID: 1,
                name: `Section ${i}`,
                xmlid: `sec_${i}`,
                childrenTree: [],
            }));
        }
        set currentAppSections(_) {}
        async adapt() {
            this.currentAppSectionsExtra = [this.currentAppSections.at(-1)];
            return this.render();
        }
    }

    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => false });
    await mountWithCleanup(MyNavbar);
    await animationFrame();

    expect(".o_menu_sections_more button[title='More Menu']").toHaveAttribute(
        "data-hotkey",
        "0",
    );
});

test("Do not execute adapt when navbar is destroyed", async () => {
    expect.assertions(3);

    class MyNavbar extends NavBar {
        async adapt() {
            expect.step("adapt NavBar");
            return super.adapt();
        }
    }

    await makeMockEnv();

    getService("menu").setCurrentMenu(1);
    const navbar = await mountWithCleanup(MyNavbar);
    expect.verifySteps(["adapt NavBar"]);
    await resize();
    await runAllTimers();
    expect.verifySteps(["adapt NavBar"]);
    await resize();
    destroy(navbar);
    await runAllTimers();
    expect.verifySteps([]);
});

test.tags("desktop");
test("the icon-only navbar toggles carry an accessible name", async () => {
    defineMenus([
        {
            id: 1,
            children: [{ id: 10 }, { id: 11 }, { id: 12 }, { id: 13 }, { id: 14 }],
        },
    ]);
    await resize({ width: 300 });
    const env = await makeMockEnv();
    Object.defineProperty(env, "isSmall", { get: () => false });
    getService("menu").setCurrentMenu(1);
    await mountWithCleanup(NavBar);
    await waitNavbarAdaptation();

    expect("a.o_menu_toggle").toHaveAttribute("aria-label", "Home menu");
    expect("a.o_menu_toggle").toHaveAttribute("title", "Home menu");
    expect(".o_menu_sections_more button").toHaveAttribute("aria-label", "More Menu");
    expect(".o_menu_sections_more button i").toHaveAttribute("aria-hidden", "true");
});

test.tags("desktop");
test("the systray holds only its items, with no filler elements between them", async () => {
    systrayRegistry.add("addon.seconditem", { Component: MySystrayItem });
    await mountWithCleanup(NavBar);
    const systray = document.querySelector(".o_menu_systray");
    const filler = [...systray.children].filter(
        (el) => !el.hasAttributes() && !el.childNodes.length,
    );
    expect(filler.length).toBe(0, {
        message: `empty filler elements in the systray: ${filler.length}`,
    });
    expect(systray.children.length).toBe(systrayRegistry.getEntries().length);
});

test.tags("mobile");
test("the toggle follows the home menu opening", async () => {
    await mountWithCleanup(NavBar);
    const homeMenu = getService("home_menu");
    expect(".o_menu_toggle .fa-bars").toHaveCount(1, {
        message: "in an app: the hamburger",
    });

    homeMenu.hasHomeMenu = true;
    await animationFrame();
    expect(".o_menu_toggle .fa-bars").toHaveCount(0);
    expect(".o_menu_toggle svg.o_menu_toggle_icon").toHaveCount(1, {
        message: "the launcher is up: the grid icon",
    });

    homeMenu.hasHomeMenu = false;
    await animationFrame();
    expect(".o_menu_toggle .fa-bars").toHaveCount(1);
});

test.tags("desktop");
test("the navbar hides the breadcrumb's slot, not the breadcrumb another component put in it", async () => {
    await mountWithCleanup(NavBar);
    const homeMenu = getService("home_menu");
    const slot = queryOne(".o_navbar_breadcrumbs");
    expect(slot).not.toHaveClass("o_hidden");

    homeMenu.hasHomeMenu = true;
    await animationFrame();
    expect(".o_navbar_breadcrumbs").toHaveClass("o_hidden", {
        message: "the home menu is not in an app, so the app's parts go",
    });

    homeMenu.hasHomeMenu = false;
    await animationFrame();
    expect(".o_navbar_breadcrumbs").not.toHaveClass("o_hidden");
});

test("a systray item that throws while rendering is dropped and the navbar still renders", async () => {
    class CrashingItem extends Component {
        static props = ["*"];
        static template = xml`<li class="my-crashing-item" t-out="this.boom"/>`;
        get boom() {
            throw new Error("render boom");
        }
    }
    systrayRegistry.add("addon.crashing", { Component: CrashingItem });
    expect.errors(1);
    await mountWithCleanup(NavBar);
    await animationFrame();
    expect(".o_menu_systray").toHaveCount(1);
    expect("li.my-item").toHaveCount(1);
    expect("li.my-crashing-item").toHaveCount(0);
    expect.verifyErrors(["Error: render boom"]);
});
