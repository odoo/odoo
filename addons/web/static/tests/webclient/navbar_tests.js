/** @odoo-module **/

import { actionService } from "../../src/actions/action_service";
import { browser } from "../../src/core/browser";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { notificationService } from "../../src/notifications/notification_service";
import { uiService } from "../../src/services/ui_service";
import { patch, unpatch } from "../../src/utils/patch";
import { NavBar } from "../../src/webclient/navbar/navbar";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, nextTick } from "../helpers/utils";
import { Registry } from "./../../src/core/registry";
import { menuService } from "./../../src/services/menu_service";

const { Component, mount, tags } = owl;
const { xml } = tags;

class MySystrayItem extends Component {}
MySystrayItem.template = xml`<li class="my-item">my item</li>`;
let baseConfig;

QUnit.module("Navbar", {
  async beforeEach() {
    const serviceRegistry = new Registry();
    serviceRegistry.add("menu", menuService);
    serviceRegistry.add("action", actionService);
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("ui", uiService);
    const menus = {
      root: { id: "root", children: [1], name: "root", appID: "root" },
      1: { id: 1, children: [], name: "App0", appID: 1 },
    };
    const serverData = { menus };
    const systrayRegistry = new Registry();
    systrayRegistry.add("addon.myitem", MySystrayItem);
    patch(browser, "mock.navbar_tests", {
      setTimeout: (handler, delay, ...args) => handler(...args),
      clearTimeout: () => {},
    });
    baseConfig = { serviceRegistry, serverData, systrayRegistry };
  },
  afterEach() {
    unpatch(browser, "mock.navbar_tests");
  },
});

QUnit.test("can be rendered", async (assert) => {
  const env = await makeTestEnv(baseConfig);
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });
  assert.containsOnce(
    navbar.el,
    ".o_navbar_apps_menu button.o_dropdown_toggler",
    "1 apps menu toggler present"
  );
  navbar.destroy();
});

QUnit.test("dropdown menu can be toggled", async (assert) => {
  const env = await makeTestEnv(baseConfig);
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });
  const dropdown = navbar.el.querySelector(".o_navbar_apps_menu");
  await click(dropdown, "button.o_dropdown_toggler");
  assert.containsOnce(dropdown, "ul.o_dropdown_menu");
  await click(dropdown, "button.o_dropdown_toggler");
  assert.containsNone(dropdown, "ul.o_dropdown_menu");
  navbar.destroy();
});

QUnit.test("data-menu-xmlid attribute on AppsMenu items", async (assert) => {
  baseConfig.serverData.menus = {
    root: { id: "root", children: [1, 2], name: "root", appID: "root" },
    1: { id: 1, children: [3, 4], name: "App0 with xmlid", appID: 1, xmlid: "wowl" },
    2: { id: 2, children: [], name: "App1 without xmlid", appID: 2 },
    3: { id: 3, children: [], name: "Menu without children", appID: 1, xmlid: "menu_3" },
    4: { id: 4, children: [5], name: "Menu with children", appID: 1 },
    5: { id: 5, children: [], name: "Sub menu", appID: 1, xmlid: "menu_5" },
  };
  const env = await makeTestEnv(baseConfig);
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });

  // check apps
  const appsMenu = navbar.el.querySelector(".o_navbar_apps_menu");
  await click(appsMenu, "button.o_dropdown_toggler");
  const menuItems = appsMenu.querySelectorAll("li");
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
  assert.containsOnce(navbar, ".o_menu_sections .o_dropdown_item[data-menu-xmlid=menu_3]");

  // check sub menus
  await click(navbar.el.querySelector(".o_menu_sections .o_dropdown_toggler"));
  assert.containsOnce(navbar, ".o_menu_sections .o_dropdown_item[data-menu-xmlid=menu_5]");

  navbar.destroy();
});

QUnit.test("navbar can display current active app", async (assert) => {
  const env = await makeTestEnv(baseConfig);
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });
  const dropdown = navbar.el.querySelector(".o_navbar_apps_menu");
  // Open apps menu
  await click(dropdown, "button.o_dropdown_toggler");
  assert.containsOnce(
    dropdown,
    "ul.o_dropdown_menu li.o_dropdown_item:not(.o_dropdown_active)",
    "should not show the current active app as the menus service has not loaded an app yet"
  );

  // Activate an app
  env.services.menu.setCurrentMenu(1);
  await nextTick();
  assert.containsOnce(
    dropdown,
    "ul.o_dropdown_menu li.o_dropdown_item.o_dropdown_active",
    "should show the current active app"
  );
  navbar.destroy();
});

QUnit.test("navbar can display systray items", async (assert) => {
  const env = await makeTestEnv(baseConfig);
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });
  assert.containsOnce(navbar.el, "li.my-item");
  navbar.destroy();
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

  const systrayRegistry = new Registry();
  systrayRegistry.add("addon.myitem2", MyItem2);
  systrayRegistry.add("addon.myitem1", MyItem1, { sequence: 0 });
  systrayRegistry.add("addon.myitem3", MyItem3, { sequence: 100 });
  systrayRegistry.add("addon.myitem4", MyItem4);
  const env = await makeTestEnv({ ...baseConfig, systrayRegistry });
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });
  const menuSystray = navbar.el.getElementsByClassName("o_menu_systray")[0];
  assert.containsN(menuSystray, "li", 4, "four systray items should be displayed");
  assert.strictEqual(menuSystray.innerText, "my item 3\nmy item 4\nmy item 2\nmy item 1");
  navbar.destroy();
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
  // Set menu and mount
  env.services.menu.setCurrentMenu(1);
  const target = getFixture();
  const navbar = await mount(MyNavbar, { env, target });
  assert.containsN(
    navbar.el,
    ".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)",
    3,
    "should have 3 menu sections displayed (that are not the 'more' menu)"
  );
  assert.containsOnce(
    navbar.el,
    ".o_menu_sections_more.d-none",
    "the 'more' menu should be hidden"
  );
  // Force minimal width and dispatch window resize event
  navbar.el.style.width = "0%";
  window.dispatchEvent(new Event("resize"));
  await nextTick();
  assert.containsOnce(
    navbar.el,
    ".o_menu_sections > *:not(.d-none)",
    "only one menu section should be displayed"
  );
  assert.containsOnce(
    navbar.el,
    ".o_menu_sections_more:not(.d-none)",
    "the displayed menu section should be the 'more' menu"
  );
  // Open the more menu
  await click(navbar.el, ".o_menu_sections_more .o_dropdown_toggler");
  assert.deepEqual(
    [...navbar.el.querySelectorAll(".o_dropdown_menu > *")].map((el) => el.textContent),
    ["Section 10", "Section 11", "Section 12", "Section 120", "Section 121", "Section 122"],
    "'more' menu should contain all hidden sections in correct order"
  );
  // Reset to full width and dispatch window resize event
  navbar.el.style.width = "100%";
  window.dispatchEvent(new Event("resize"));
  await nextTick();
  assert.containsN(
    navbar.el,
    ".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)",
    3,
    "should have 3 menu sections displayed (that are not the 'more' menu)"
  );
  assert.containsOnce(
    navbar.el,
    ".o_menu_sections_more.d-none",
    "the 'more' menu should be hidden"
  );
  // Check the navbar adaptation calls
  assert.verifySteps([
    "adapt -> hide 0/3 sections",
    "adapt -> hide 3/3 sections",
    "adapt -> hide 0/3 sections",
  ]);
  navbar.destroy();
});

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

  // Set App1 menu and mount
  env.services.menu.setCurrentMenu(1);
  const target = getFixture();
  const navbar = await mount(NavBar, { env, target });

  // Force minimal width and dispatch window resize event
  navbar.el.style.width = "0%";
  window.dispatchEvent(new Event("resize"));
  await nextTick();
  assert.containsOnce(
    navbar.el,
    ".o_menu_sections > *:not(.d-none)",
    "only one menu section should be displayed"
  );
  assert.containsOnce(
    navbar.el,
    ".o_menu_sections_more:not(.d-none)",
    "the displayed menu section should be the 'more' menu"
  );

  // Open the more menu
  await click(navbar.el, ".o_menu_sections_more .o_dropdown_toggler");
  assert.deepEqual(
    [...navbar.el.querySelectorAll(".o_dropdown_menu > *")].map((el) => el.textContent),
    ["Section 10", "Section 11", "Section 12", "Section 120", "Section 121", "Section 122"],
    "'more' menu should contain App1 sections"
  );
  // Close the more menu
  await click(navbar.el, ".o_menu_sections_more .o_dropdown_toggler");

  // Set App2 menu
  env.services.menu.setCurrentMenu(2);
  await nextTick();

  // Open the more menu
  await click(navbar.el, ".o_menu_sections_more .o_dropdown_toggler");
  assert.deepEqual(
    [...navbar.el.querySelectorAll(".o_dropdown_menu > *")].map((el) => el.textContent),
    ["Section 20", "Section 21", "Section 22", "Section 220", "Section 221", "Section 222"],
    "'more' menu should contain App2 sections"
  );
  navbar.destroy();
});
