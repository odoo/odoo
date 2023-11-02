/** @odoo-module **/

/**
 * The purpose of this test is to click on every installed App and then open each
 * view. On each view, click on each filter.
 */

import { App } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ORM } from "@web/core/orm_service";
import { browser } from "@web/core/browser/browser";

const MOUSE_EVENTS = ["mouseover", "mouseenter", "mousedown", "mouseup", "click"];
const BLACKLISTED_MENUS = [
    "base.menu_theme_store", // Open a new tab
    "base.menu_third_party", // Open a new tab
    "event.menu_event_registration_desk", // there's no way to come back from this menu (tablet mode)
    "hr_attendance.menu_hr_attendance_kiosk_no_user_mode", // same here (tablet mode)
    "account.menu_action_account_bank_journal_form", // Modal in an iFrame
];
// If you change this selector, adapt Studio test "Studio icon matches the clickbot selector"
const STUDIO_SYSTRAY_ICON_SELECTOR = ".o_web_studio_navbar_item:not(.o_disabled) i";

let isEnterprise;
let appsMenusOnly = false;
let calledRPC;
let actionCount;
let env;
let studioCount;

let appIndex;
let menuIndex;
let subMenuIndex;
let testedApps;
let testedMenus;
let testedFilters;
let testedModals;

let unPatchORM;

/**
 * Hook on specific activities of the webclient to detect when to move forward.
 * This should be done only once.
 */
function setup() {
    unPatchORM = patch(ORM.prototype, {
        async call(model, method, args = [], kwargs = {}) {
            calledRPC.push(`${model}.${method}`);
            try {
                return await super.call(...arguments);
            } finally {
                calledRPC.splice(calledRPC.indexOf(`${model}.${method}`), 1);
            }
        },
    });
    env = odoo.__WOWL_DEBUG__.root.env;
    env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", uiUpdate);
    actionCount = 0;
    calledRPC = [];
    studioCount = 0;
    testedApps = [];
    testedMenus = [];
    testedFilters = 0;
    testedModals = 0;
    appIndex = 0;
    menuIndex = 0;
    subMenuIndex = 0;
    isEnterprise = odoo.info && odoo.info.isEnterprise;
}

function uiUpdate() {
    actionCount++;
}

function cleanup() {
    unPatchORM();
    env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", uiUpdate);
}

/**
 * Returns a promise that resolves after the next animation frame.
 *
 * @returns {Promise}
 */
async function waitForNextAnimationFrame() {
    await new Promise(browser.setTimeout);
    await new Promise((r) => requestAnimationFrame(r));
}

/**
 * Simulate all of the mouse events triggered during a click action.
 *
 * @param {EventTarget} target the element on which to perform the click
 * @param {string} elDescription description of the item
 * @returns {Promise} resolved after next animation frame
 */
async function triggerClick(target, elDescription) {
    if (target) {
        if (elDescription) {
            browser.console.log(`Clicking on: ${elDescription}`);
        }
    } else {
        throw new Error(`No element "${elDescription}" found.`);
    }
    MOUSE_EVENTS.forEach((type) => {
        const event = new MouseEvent(type, { bubbles: true, cancelable: true, view: window });
        target.dispatchEvent(event);
    });
    await waitForNextAnimationFrame();
}

/**
 * Wait a certain amount of time for a condition to occur
 *
 * @param {function} stopCondition a function that returns a boolean
 * @returns {Promise} that is rejected if the timeout is exceeded
 */
async function waitForCondition(stopCondition) {
    const interval = 25;
    const initialTime = 30000;
    let timeLimit = initialTime;

    function hasPendingRPC() {
        return calledRPC.length > 0;
    }
    function hasScheduledTask() {
        let size = 0;
        for (const app of App.apps) {
            size += app.scheduler.tasks.size;
        }
        return size > 0;
    }

    while (!stopCondition() || hasPendingRPC() || hasScheduledTask()) {
        if (document.querySelector(".o_error_dialog")) {
            throw new Error("Error dialog detected");
        }
        if (timeLimit <= 0) {
            throw new Error(
                `Timeout, the clicked element took more than ${initialTime / 1000} seconds to load`
            );
        }
        await new Promise((resolve) => setTimeout(resolve, interval));
        timeLimit -= interval;
    }
}

/**
 * Make sure the home menu is open (enterprise only)
 */
async function ensureHomeMenu() {
    const homeMenu = document.querySelector(".o_home_menu");
    if (!homeMenu) {
        let menuToggle = document.querySelector("nav.o_main_navbar > a.o_menu_toggle");
        if (!menuToggle) {
            // In the Barcode application, there is no navbar. So you have to click
            // on the o_stock_barcode_menu button which is the equivalent of
            // the o_menu_toggle button in the navbar.
            menuToggle = document.querySelector(".o_stock_barcode_menu");
        }
        await triggerClick(menuToggle, "home menu toggle button");
        await waitForCondition(() => document.querySelector(".o_home_menu"));
    }
}

/**
 * Make sure the apps menu is open (community only)
 */
async function ensureAppsMenu() {
    const appsMenu = document.querySelector(".o_navbar_apps_menu .dropdown-menu");
    if (!appsMenu) {
        const toggler = document.querySelector(".o_navbar_apps_menu .dropdown-toggle");
        await triggerClick(toggler, "apps menu toggle button");
        await waitForCondition(() => document.querySelector(".o_navbar_apps_menu .dropdown-menu"));
    }
}

/**
 * Return the next menu to test, and update the internal counters.
 *
 * @returns {DomElement}
 */
async function getNextMenu() {
    const menus = document.querySelectorAll(
        ".o_menu_sections > .dropdown > .dropdown-toggle, .o_menu_sections > .dropdown-item"
    );
    if (menuIndex === menus.length) {
        menuIndex = 0;
        return; // all menus done
    }
    let menu = menus[menuIndex];
    if (menu.classList.contains("dropdown-toggle")) {
        // the current menu is a dropdown toggler -> open it and pick a menu inside the dropdown
        if (!menu.nextElementSibling) {
            // might already be opened if the last menu was blacklisted
            await triggerClick(menu, "menu toggler");
        }
        const dropdown = menu.nextElementSibling;
        if (!dropdown) {
            menuIndex = 0; // empty More menu has no dropdown (FIXME?)
            return;
        }
        const items = dropdown.querySelectorAll(".dropdown-item");
        menu = items[subMenuIndex];
        if (subMenuIndex === items.length - 1) {
            // this is the last item, so go to the next menu
            menuIndex++;
            subMenuIndex = 0;
        } else {
            // this isn't the last item, so increment the index inside this dropdown
            subMenuIndex++;
        }
    } else {
        // the current menu isn't a dropdown, so go to the next menu
        menuIndex++;
    }
    return menu;
}

/**
 * Return the next app to test, and update the internal counter.
 *
 * @returns {DomElement}
 */
async function getNextApp() {
    let apps;
    if (isEnterprise) {
        await ensureHomeMenu();
        apps = document.querySelectorAll(".o_apps .o_app");
    } else {
        await ensureAppsMenu();
        apps = document.querySelectorAll(".o_navbar_apps_menu .dropdown-item");
    }
    const app = apps[appIndex];
    appIndex++;
    return app;
}

/**
 * Test Studio
 * Click on the Studio systray item to enter Studio, and simply leave it once loaded.
 */
async function testStudio() {
    const studioIcon = document.querySelector(STUDIO_SYSTRAY_ICON_SELECTOR);
    if (!studioIcon) {
        return;
    }
    // Open the filter menu dropdown
    await triggerClick(studioIcon, "entering studio");
    await waitForCondition(() => document.querySelector(".o_in_studio"));
    await triggerClick(document.querySelector(".o_web_studio_leave"), "leaving studio");
    await waitForCondition(() =>
        document.querySelector(".o_main_navbar:not(.o_studio_navbar) .o_menu_toggle")
    );
    studioCount++;
}

/**
 * Test filters
 * Click on each filter in the control pannel
 */
async function testFilters() {
    if (appsMenusOnly === true) {
        return;
    }
    const searchBarMenu = document.querySelector(
        ".o_control_panel .dropdown-toggle.o_searchview_dropdown_toggler"
    );
    if (!searchBarMenu) {
        return;
    }
    // Open the search bar menu dropdown
    await triggerClick(searchBarMenu);
    const filterMenuButton = document.querySelector(
        ".o_control_panel .o_dropdown_container.o_filter_menu"
    );
    // Is there a filter menu in the search bar
    if (!filterMenuButton) {
        return;
    }

    // Avoid the "Custom Filter" menu item (it don't have the class .o_menu_item)
    const simpleFilterSel =
        ".o_control_panel .o_filter_menu > .dropdown-item.o_menu_item:not(.o_add_custom_filter)";
    const dateFilterSel = ".o_control_panel .o_filter_menu > .o_accordion";
    const filterMenuItems = document.querySelectorAll(`${simpleFilterSel},${dateFilterSel}`);
    browser.console.log(`Testing ${filterMenuItems.length} filters`);
    testedFilters += filterMenuItems.length;
    for (const filter of filterMenuItems) {
        // Date filters
        if (filter.classList.contains("o_accordion")) {
            // If a fitler has options, it will simply unfold and show all options.
            await triggerClick(
                filter.querySelector(".o_accordion_toggle"),
                `filter "${filter.innerText.trim()}"`
            );

            // If a fitler has options, it will simply unfold and show all options.
            // We then click on the first one.
            const firstOption = filter.querySelector(
                ".o_accordion > .o_accordion_values > .dropdown-item"
            );
            if (firstOption) {
                await triggerClick(firstOption, `filter option "${firstOption.innerText.trim()}"`);
                await waitForCondition(() => true);
            }
        } else {
            await triggerClick(filter, `filter "${filter.innerText.trim()}"`);
            await waitForCondition(() => true);
        }
    }
}

/**
 * Orchestrate the test of views
 * This function finds the buttons that permit to switch views and orchestrate
 * the click on each of them
 * @returns {Promise}
 */
async function testViews() {
    if (appsMenusOnly === true) {
        return;
    }
    const switchButtons = document.querySelectorAll(
        "nav.o_cp_switch_buttons > button.o_switch_view:not(.active):not(.o_map)"
    );
    for (const switchButton of switchButtons) {
        // Only way to get the viewType from the switchButton
        const viewType = [...switchButton.classList]
            .find((cls) => cls !== "o_switch_view" && cls.startsWith("o_"))
            .slice(2);
        browser.console.log(`Testing view switch: ${viewType}`);
        // timeout to avoid click debounce
        browser.setTimeout(function () {
            const target = document.querySelector(
                `nav.o_cp_switch_buttons > button.o_switch_view.o_${viewType}`
            );
            if (target) {
                triggerClick(target, `${viewType} view switcher`);
            }
        }, 250);
        await waitForCondition(() => {
            return document.querySelector(`.o_switch_view.o_${viewType}.active`) !== null;
        });
        await testStudio();
        await testFilters();
    }
}

/**
 * Test a menu item by:
 *  1 - clikcing on the menuItem
 *  2 - Orchestrate the view switch
 *
 *  @param {DomElement} element: the menu item
 *  @returns {Promise}
 */
async function testMenuItem(element) {
    const menu = element.dataset.menuXmlid;
    const menuDescription = element.innerText.trim() + " " + menu;
    if (BLACKLISTED_MENUS.includes(menu)) {
        browser.console.log(`Skipping blacklisted menu ${menuDescription}`);        
        return Promise.resolve(); // Skip black listed menus
    }
    browser.console.log(`Testing menu ${menuDescription}`);
    testedMenus.push(menu);
    const startActionCount = actionCount;
    await triggerClick(element, `menu item "${element.innerText.trim()}"`);
    try {
        let isModal = false;
        await waitForCondition(() => {
            if (document.querySelector(".o_dialog:not(.o_error_dialog)")) {
                isModal = true;
                browser.console.log(`Modal detected: ${menuDescription}`);
                testedModals++;
                return true;
            } else {
                return startActionCount !== actionCount;
            }
        });
        if (isModal) {
            await triggerClick(
                document.querySelector(".o_dialog header > .btn-close"),
                "modal close button"
            );
        } else {
            await testStudio();
            await testFilters();
            await testViews();
        }
    } catch (err) {
        browser.console.error(`Error while testing ${menuDescription}`);
        throw err;
    }
}

/**
 * Test an "App" menu item by orchestrating the following actions:
 *  1 - clicking on its menuItem
 *  2 - clicking on each view
 *  3 - clicking on each menu
 *  3.1  - clicking on each view
 * @param {DomElement} element: the App menu item
 * @returns {Promise}
 */
async function testApp(element) {
    browser.console.log(`Testing app menu: ${element.dataset.menuXmlid}`);
    testedApps.push(element.dataset.menuXmlid);
    await testMenuItem(element);
    if (appsMenusOnly === true) {
        return;
    }
    menuIndex = 0;
    subMenuIndex = 0;
    let menu = await getNextMenu();
    while (menu) {
        await testMenuItem(menu);
        menu = await getNextMenu();
    }
}

/**
 * Main function that starts orchestration of tests
 */
async function _clickEverywhere(xmlId) {
    setup();
    console.log("Starting ClickEverywhere test");
    console.log(`Odoo flavor: ${isEnterprise ? "Enterprise" : "Community"}`);
    const startTime = performance.now();
    try {
        let app;
        if (xmlId) {
            if (isEnterprise) {
                app = document.querySelector(`a.o_app.o_menuitem[data-menu-xmlid="${xmlId}"]`);
            } else {
                await triggerClick(document.querySelector(".o_navbar_apps_menu .dropdown-toggle"));
                app = document.querySelector(
                    `.o_navbar_apps_menu .dropdown-item[data-menu-xmlid="${xmlId}"]`
                );
            }
            if (!app) {
                throw new Error(`No app found for xmlid ${xmlId}`);
            }
            await testApp(app);
        } else {
            while ((app = await getNextApp())) {
                await testApp(app);
            }
        }

        console.log(`Test took ${(performance.now() - startTime) / 1000} seconds`);
        browser.console.log(`Successfully tested ${testedApps.length} apps`);
        browser.console.log(`Successfully tested ${testedMenus.length - testedApps.length} menus`);
        browser.console.log(`Successfully tested ${testedModals} modals`);
        browser.console.log(`Successfully tested ${testedFilters} filters`);
        if (studioCount > 0) {
            browser.console.log(`Successfully tested ${studioCount} views in Studio`);
        }
        browser.console.log("test successful");
    } catch (err) {
        console.log(`Test took ${(performance.now() - startTime) / 1000} seconds`);
        browser.console.error(err || "test failed");
    } finally {
        cleanup();
    }
}

function clickEverywhere(xmlId, light) {
    appsMenusOnly = light;
    browser.setTimeout(_clickEverywhere, 1000, xmlId);
}

window.clickEverywhere = clickEverywhere;
