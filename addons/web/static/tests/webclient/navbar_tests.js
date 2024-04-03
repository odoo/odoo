/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { notificationService } from "@web/core/notifications/notification_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { registry } from "@web/core/registry";
import { ormService } from "@web/core/orm_service";
import { uiService } from "@web/core/ui/ui_service";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { NavBar } from "@web/webclient/navbar/navbar";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import {
    click,
    destroy,
    getFixture,
    mount,
    nextTick,
    patchWithCleanup,
    mockTimeout,
} from "../helpers/utils";

import { Component, xml, onRendered } from "@odoo/owl";

const systrayRegistry = registry.category("systray");
const serviceRegistry = registry.category("services");

class MySystrayItem extends Component {}
MySystrayItem.template = xml`<li class="my-item">my item</li>`;
let baseConfig;
let target;

QUnit.module("Navbar", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("menu", menuService);
        serviceRegistry.add("action", actionService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("view", viewService); // #action-serv-leg-compat-js-class
        serviceRegistry.add("orm", ormService); // #action-serv-leg-compat-js-class
        systrayRegistry.add("addon.myitem", { Component: MySystrayItem });
        patchWithCleanup(browser, {
            setTimeout: (handler, delay, ...args) => handler(...args),
            clearTimeout: () => {},
        });
        const menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App0", appID: 1 },
        };
        const serverData = { menus };
        baseConfig = { serverData };
    },
});

QUnit.test("can be rendered", async (assert) => {
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });
    assert.containsOnce(
        target,
        ".o_navbar_apps_menu button.dropdown-toggle",
        "1 apps menu toggler present"
    );
});

QUnit.test("dropdown menu can be toggled", async (assert) => {
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });
    const dropdown = target.querySelector(".o_navbar_apps_menu");
    await click(dropdown, "button.dropdown-toggle");
    assert.containsOnce(dropdown, ".dropdown-menu");
    await click(dropdown, "button.dropdown-toggle");
    assert.containsNone(dropdown, ".dropdown-menu");
});

QUnit.test("href attribute on apps menu items", async (assert) => {
    baseConfig.serverData.menus = {
        root: { id: "root", children: [1], name: "root", appID: "root" },
        1: { id: 1, children: [2], name: "My app", appID: 1, actionID: 339 },
    };
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });
    const appsMenu = target.querySelector(".o_navbar_apps_menu");
    await click(appsMenu, "button.dropdown-toggle");
    const dropdownItem = target.querySelector(".o_navbar_apps_menu .dropdown-item");
    assert.strictEqual(dropdownItem.getAttribute("href"), "#menu_id=1&action=339");
});

QUnit.test("many sublevels in app menu items", async (assert) => {
    baseConfig.serverData.menus = {
        root: { id: "root", children: [1], name: "root", appID: "root" },
        1: { id: 1, children: [2], name: "My app", appID: 1 },
        2: { id: 2, children: [3], name: "My menu", appID: 1 },
        3: { id: 3, children: [4], name: "My submenu 1", appID: 1 },
        4: { id: 4, children: [5], name: "My submenu 2", appID: 1 },
        5: { id: 5, children: [6], name: "My submenu 3", appID: 1 },
        6: { id: 6, children: [7], name: "My submenu 4", appID: 1 },
        7: { id: 7, children: [8], name: "My submenu 5", appID: 1 },
        8: { id: 8, children: [9], name: "My submenu 6", appID: 1 },
        9: { id: 9, children: [], name: "My submenu 7", appID: 1 },
    };
    const env = await makeTestEnv(baseConfig);
    env.services.menu.setCurrentMenu(1);
    await mount(NavBar, target, { env });
    const firstSectionMenu = target.querySelector(".o_menu_sections .dropdown");
    await click(firstSectionMenu, "button.dropdown-toggle");
    const menuChildren = [...firstSectionMenu.querySelectorAll(".dropdown-menu > *")];
    assert.deepEqual(
        menuChildren.map((el) => ({
            text: el.textContent,
            paddingLeft: el.style.paddingLeft,
            tagName: el.tagName,
        })),
        [
            { text: "My submenu 1", paddingLeft: "20px", tagName: "DIV" },
            { text: "My submenu 2", paddingLeft: "32px", tagName: "DIV" },
            { text: "My submenu 3", paddingLeft: "44px", tagName: "DIV" },
            { text: "My submenu 4", paddingLeft: "56px", tagName: "DIV" },
            { text: "My submenu 5", paddingLeft: "68px", tagName: "DIV" },
            { text: "My submenu 6", paddingLeft: "80px", tagName: "DIV" },
            { text: "My submenu 7", paddingLeft: "92px", tagName: "A" },
        ]
    );
});

QUnit.test("data-menu-xmlid attribute on AppsMenu items", async (assert) => {
    baseConfig.serverData.menus = {
        root: { id: "root", children: [1, 2], name: "root", appID: "root" },
        1: { id: 1, children: [3, 4], name: "App0 with xmlid", appID: 1, xmlid: "wowl" },
        2: { id: 2, children: [], name: "App1 without xmlid", appID: 2 },
        3: { id: 3, children: [], name: "Menu without children", appID: 1, xmlid: "menu_3" },
        4: { id: 4, children: [5], name: "Menu with children", appID: 1, xmlid: "menu_4" },
        5: { id: 5, children: [], name: "Sub menu", appID: 1, xmlid: "menu_5" },
    };
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });

    // check apps
    const appsMenu = target.querySelector(".o_navbar_apps_menu");
    await click(appsMenu, "button.dropdown-toggle");
    const menuItems = appsMenu.querySelectorAll("a");
    assert.strictEqual(
        menuItems[0].dataset.menuXmlid,
        "wowl",
        "first menu item should have the correct data-menu-xmlid attribute set"
    );
    assert.strictEqual(
        menuItems[1].dataset.menuXmlid,
        undefined,
        "second menu item should not have any data-menu-xmlid attribute set"
    );

    // check menus
    env.services.menu.setCurrentMenu(1);
    await nextTick();
    assert.containsOnce(target, ".o_menu_sections .dropdown-item[data-menu-xmlid=menu_3]");

    // check sub menus toggler
    assert.containsOnce(target, ".o_menu_sections button.dropdown-toggle[data-menu-xmlid=menu_4]");

    // check sub menus
    await click(target.querySelector(".o_menu_sections .dropdown-toggle"));
    assert.containsOnce(target, ".o_menu_sections .dropdown-item[data-menu-xmlid=menu_5]");
});

QUnit.test("navbar can display current active app", async (assert) => {
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });
    const dropdown = target.querySelector(".o_navbar_apps_menu");
    // Open apps menu
    await click(dropdown, "button.dropdown-toggle");
    assert.containsOnce(
        dropdown,
        ".dropdown-menu .dropdown-item:not(.focus)",
        "should not show the current active app as the menus service has not loaded an app yet"
    );

    // Activate an app
    env.services.menu.setCurrentMenu(1);
    await nextTick();
    assert.containsOnce(
        dropdown,
        ".dropdown-menu .dropdown-item.focus",
        "should show the current active app"
    );
});

QUnit.test("navbar can display systray items", async (assert) => {
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });
    assert.containsOnce(target, "li.my-item");
});

QUnit.test("navbar can display systray items ordered based on their sequence", async (assert) => {
    class MyItem1 extends Component {}
    MyItem1.template = xml`<li class="my-item-1">my item 1</li>`;
    class MyItem2 extends Component {}
    MyItem2.template = xml`<li class="my-item-2">my item 2</li>`;
    class MyItem3 extends Component {}
    MyItem3.template = xml`<li class="my-item-3">my item 3</li>`;
    class MyItem4 extends Component {}
    MyItem4.template = xml`<li class="my-item-4">my item 4</li>`;

    clearRegistryWithCleanup(systrayRegistry);
    systrayRegistry.add("addon.myitem2", { Component: MyItem2 });
    systrayRegistry.add("addon.myitem1", { Component: MyItem1 }, { sequence: 0 });
    systrayRegistry.add("addon.myitem3", { Component: MyItem3 }, { sequence: 100 });
    systrayRegistry.add("addon.myitem4", { Component: MyItem4 });
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, { env });
    const menuSystray = target.getElementsByClassName("o_menu_systray")[0];
    assert.containsN(menuSystray, "li", 4, "four systray items should be displayed");
    assert.strictEqual(menuSystray.innerText, "my item 3\nmy item 4\nmy item 2\nmy item 1");
});

QUnit.test("navbar updates after adding a systray item", async (assert) => {
    class MyItem1 extends Component {}
    MyItem1.template = xml`<li class="my-item-1">my item 1</li>`;

    clearRegistryWithCleanup(systrayRegistry);
    systrayRegistry.add("addon.myitem1", { Component: MyItem1 });

    const env = await makeTestEnv(baseConfig);

    patchWithCleanup(NavBar.prototype, {
        setup() {
            onRendered(() => {
                if (!systrayRegistry.contains("addon.myitem2")) {
                    class MyItem2 extends Component {}
                    MyItem2.template = xml`<li class="my-item-2">my item 2</li>`;
                    systrayRegistry.add("addon.myitem2", { Component: MyItem2 });
                }
            });
            this._super();
        },
    });

    await mount(NavBar, target, { env });
    const menuSystray = target.getElementsByClassName("o_menu_systray")[0];
    assert.containsN(menuSystray, "li", 2, "2 systray items should be displayed");
});

QUnit.test("can adapt with 'more' menu sections behavior", async (assert) => {
    class MyNavbar extends NavBar {
        async adapt() {
            await super.adapt();
            const sectionsCount = this.currentAppSections.length;
            const hiddenSectionsCount = this.currentAppSectionsExtra.length;
            assert.step(`adapt -> hide ${hiddenSectionsCount}/${sectionsCount} sections`);
        }
    }
    const newMenus = {
        root: { id: "root", children: [1, 2], name: "root", appID: "root" },
        1: { id: 1, children: [10, 11, 12], name: "App0", appID: 1 },
        10: { id: 10, children: [], name: "Section 10", appID: 1 },
        11: { id: 11, children: [], name: "Section 11", appID: 1 },
        12: { id: 12, children: [120, 121, 122], name: "Section 12", appID: 1 },
        120: { id: 120, children: [], name: "Section 120", appID: 1 },
        121: { id: 121, children: [], name: "Section 121", appID: 1 },
        122: { id: 122, children: [], name: "Section 122", appID: 1 },
    };
    baseConfig.serverData.menus = newMenus;
    const env = await makeTestEnv(baseConfig);

    // Force the parent width, to make this test independent of screen size
    target.style.width = "1080px";

    // Set menu and mount
    env.services.menu.setCurrentMenu(1);
    await mount(MyNavbar, target, { env });
    assert.containsN(
        target,
        ".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)",
        3,
        "should have 3 menu sections displayed (that are not the 'more' menu)"
    );
    assert.containsNone(target, ".o_menu_sections_more", "the 'more' menu should not exist");
    // Force minimal width and dispatch window resize event
    target.style.width = "0%";
    window.dispatchEvent(new Event("resize"));
    await nextTick();
    assert.containsOnce(
        target,
        ".o_menu_sections > *:not(.d-none)",
        "only one menu section should be displayed"
    );
    assert.containsOnce(
        target,
        ".o_menu_sections_more:not(.d-none)",
        "the displayed menu section should be the 'more' menu"
    );
    // Open the more menu
    await click(target, ".o_menu_sections_more .dropdown-toggle");
    assert.deepEqual(
        [...target.querySelectorAll(".dropdown-menu > *")].map((el) => el.textContent),
        ["Section 10", "Section 11", "Section 12", "Section 120", "Section 121", "Section 122"],
        "'more' menu should contain all hidden sections in correct order"
    );
    // Reset to full width and dispatch window resize event
    target.style.width = "100%";
    window.dispatchEvent(new Event("resize"));
    await nextTick();
    assert.containsN(
        target,
        ".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)",
        3,
        "should have 3 menu sections displayed (that are not the 'more' menu)"
    );
    assert.containsNone(target, ".o_menu_sections_more", "the 'more' menu should not exist");
    // Check the navbar adaptation calls
    assert.verifySteps([
        "adapt -> hide 0/3 sections",
        "adapt -> hide 3/3 sections",
        "adapt -> hide 0/3 sections",
    ]);
});

QUnit.test(
    "'more' menu sections adaptations do not trigger render in some cases",
    async (assert) => {
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

        const newMenus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [11, 12, 13], name: "App1", appID: 1 },
            11: { id: 11, children: [], name: "Section 1", appID: 1 },
            12: { id: 12, children: [], name: "Section 2", appID: 1 },
            13: { id: 13, children: [], name: "Section 3", appID: 1 },
        };
        baseConfig.serverData.menus = newMenus;

        // Force the parent width, to make this test independent of screen size
        target.style.width = "600px";

        const env = await makeTestEnv(baseConfig);
        const navbar = await mount(MyNavbar, target, { env });
        assert.strictEqual(navbar.currentAppSections.length, 0, "0 app sub menus");
        assert.strictEqual(target.querySelector(".o_navbar").offsetWidth, 600);
        assert.strictEqual(adaptCount, 1);
        assert.strictEqual(
            adaptRenderCount,
            0,
            "during adapt, render not triggered as the navbar has no app sub menus"
        );

        // Force minimal width and dispatch window resize event
        target.querySelector(".o_navbar").style.width = "0%";
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        assert.strictEqual(target.querySelector(".o_navbar").offsetWidth, 0);
        assert.strictEqual(adaptCount, 2);
        assert.strictEqual(
            adaptRenderCount,
            0,
            "during adapt, render not triggered as the navbar has no app sub menus"
        );

        // Set menu
        env.services.menu.setCurrentMenu(1);
        await nextTick();
        assert.strictEqual(navbar.currentAppSections.length, 3, "3 app sub menus");
        assert.strictEqual(
            navbar.currentAppSectionsExtra.length,
            3,
            "all app sub menus are inside the more menu"
        );
        assert.strictEqual(adaptCount, 3);
        assert.strictEqual(
            adaptRenderCount,
            1,
            "during adapt, render triggered as the navbar does not have enough space for app sub menus"
        );

        // Force 40% width and dispatch window resize event
        target.querySelector(".o_navbar").style.width = "40%";
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        assert.strictEqual(
            navbar.currentAppSectionsExtra.length,
            3,
            "all app sub menus are STILL inside the more menu"
        );
        assert.strictEqual(adaptCount, 4);
        assert.strictEqual(
            adaptRenderCount,
            1,
            "during adapt, render not triggered as the more menu dropdown is STILL the same"
        );

        // Reset to full width and dispatch window resize event
        target.querySelector(".o_navbar").style.width = "100%";
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        assert.strictEqual(navbar.currentAppSections.length, 3, "still 3 app sub menus");
        assert.strictEqual(
            navbar.currentAppSectionsExtra.length,
            0,
            "all app sub menus are NO MORE inside the more menu"
        );
        assert.strictEqual(adaptCount, 5);
        assert.strictEqual(
            adaptRenderCount,
            2,
            "during adapt, render triggered as the more menu dropdown is NO MORE the same"
        );
    }
);

QUnit.test("'more' menu sections properly updated on app change", async (assert) => {
    const newMenus = {
        root: { id: "root", children: [1, 2], name: "root", appID: "root" },
        // First App
        1: { id: 1, children: [10, 11, 12], name: "App1", appID: 1 },
        10: { id: 10, children: [], name: "Section 10", appID: 1 },
        11: { id: 11, children: [], name: "Section 11", appID: 1 },
        12: { id: 12, children: [120, 121, 122], name: "Section 12", appID: 1 },
        120: { id: 120, children: [], name: "Section 120", appID: 1 },
        121: { id: 121, children: [], name: "Section 121", appID: 1 },
        122: { id: 122, children: [], name: "Section 122", appID: 1 },
        // Second App
        2: { id: 2, children: [20, 21, 22], name: "App2", appID: 2 },
        20: { id: 20, children: [], name: "Section 20", appID: 2 },
        21: { id: 21, children: [], name: "Section 21", appID: 2 },
        22: { id: 22, children: [220, 221, 222], name: "Section 22", appID: 2 },
        220: { id: 220, children: [], name: "Section 220", appID: 2 },
        221: { id: 221, children: [], name: "Section 221", appID: 2 },
        222: { id: 222, children: [], name: "Section 222", appID: 2 },
    };
    baseConfig.serverData.menus = newMenus;
    const env = await makeTestEnv(baseConfig);

    // Force the parent width, to make this test independent of screen size
    target.style.width = "1080px";

    // Set App1 menu and mount
    env.services.menu.setCurrentMenu(1);
    await mount(NavBar, target, { env });

    // Force minimal width and dispatch window resize event
    target.style.width = "0%";
    window.dispatchEvent(new Event("resize"));
    await nextTick();
    assert.containsOnce(
        target,
        ".o_menu_sections > *:not(.d-none)",
        "only one menu section should be displayed"
    );
    assert.containsOnce(
        target,
        ".o_menu_sections_more:not(.d-none)",
        "the displayed menu section should be the 'more' menu"
    );

    // Open the more menu
    await click(target, ".o_menu_sections_more .dropdown-toggle");
    assert.deepEqual(
        [...target.querySelectorAll(".dropdown-menu > *")].map((el) => el.textContent),
        ["Section 10", "Section 11", "Section 12", "Section 120", "Section 121", "Section 122"],
        "'more' menu should contain App1 sections"
    );
    // Close the more menu
    await click(target, ".o_menu_sections_more .dropdown-toggle");

    // Set App2 menu
    env.services.menu.setCurrentMenu(2);
    await nextTick();

    // Open the more menu
    await click(target, ".o_menu_sections_more .dropdown-toggle");
    assert.deepEqual(
        [...target.querySelectorAll(".dropdown-menu > *")].map((el) => el.textContent),
        ["Section 20", "Section 21", "Section 22", "Section 220", "Section 221", "Section 222"],
        "'more' menu should contain App2 sections"
    );
});

QUnit.test("Do not execute adapt when navbar is destroyed", async (assert) => {
    assert.expect(5);

    const { execRegisteredTimeouts } = mockTimeout();
    class MyNavbar extends NavBar {
        async adapt() {
            assert.step("adapt NavBar");
            return super.adapt();
        }
    }
    const env = await makeTestEnv(baseConfig);

    // Set menu and mount
    env.services.menu.setCurrentMenu(1);
    const navbar = await mount(MyNavbar, target, { env });
    assert.verifySteps(["adapt NavBar"]);
    window.dispatchEvent(new Event("resize"));
    execRegisteredTimeouts();
    assert.verifySteps(["adapt NavBar"]);
    window.dispatchEvent(new Event("resize"));
    destroy(navbar);
    execRegisteredTimeouts();
    assert.verifySteps([]);
});
