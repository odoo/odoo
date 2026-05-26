/**
 * The purpose of this test is to click on every installed App and then open each
 * view. On each view, click on each filter.
 */

import { reactive } from "@web/owl2/utils";
import { App, effect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { ClickbotOverlay } from "./clickbot_overlay";

export const SUCCESS_SIGNAL = "clickbot test succeeded";

const MOUSE_EVENTS = ["mouseover", "mouseenter", "mousedown", "mouseup", "click"];
const BLACKLISTED_MENUS = new Set([
    "base.menu_theme_store", // Open a new tab
    "base.menu_third_party", // Open a new tab
    "event.menu_event_registration_desk", // there's no way to come back from this menu (tablet mode)
    "hr_attendance.menu_action_open_form", // same here (tablet mode)
    "hr_attendance.menu_hr_attendance_onboarding", // same here (tablet mode)
    "mrp_workorder.menu_mrp_workorder_root", // same here (tablet mode)
    "pos_enterprise.menu_point_kitchen_display_root", // conditional menu that may leads to frontend
    "mail.menu_settings", // menu that leads to another App
]);
// If you change this selector, adapt Studio test "Studio icon matches the clickbot selector"
const STUDIO_SYSTRAY_ICON_SELECTOR = ".o_web_studio_navbar_item:not(.o_disabled) i";

let state;
let calledRPC;
let errorRPC;
let actionCount;
let env;
let disposeEffect = () => {};
let removeOverlay = () => {};

/**
 * Hook on specific activities of the webclient to detect when to move forward.
 * This should be done only once.
 */
function setup(light, currentState) {
    env = odoo.__WOWL_DEBUG__.root.env;

    env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", uiUpdate);
    rpcBus.addEventListener("RPC:REQUEST", onRPCRequest);
    rpcBus.addEventListener("RPC:RESPONSE", onRPCResponse);

    state = reactive(
        currentState || {
            light,
            studioCount: 0,
            testedApps: [],
            testedMenus: [],
            testedFilters: 0,
            testedModals: 0,
            appIndex: 0,
            menuIndex: 0,
            totalApps: 0,
            totalMenus: 0,
            currentApp: "",
            currentMenu: "",
            done: false,
            timeTaken: 0,
            error: "",
        }
    );
    removeOverlay = env.services.overlay.add(ClickbotOverlay, {
        state,
        onClose: () => removeOverlay(),
    });
    disposeEffect = effect(() => {
        browser.localStorage.setItem("running.clickbot", JSON.stringify(state));
    });

    actionCount = 0;
    calledRPC = {};
    errorRPC = undefined;
}

function onRPCRequest({ detail }) {
    calledRPC[detail.data.id] = detail.url;
}

function onRPCResponse({ detail }) {
    delete calledRPC[detail.data.id];
    if (detail.error) {
        errorRPC = { ...detail };
    }
}

function uiUpdate() {
    actionCount++;
}

function cleanup() {
    disposeEffect();
    browser.localStorage.removeItem("running.clickbot");
    env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", uiUpdate);
    rpcBus.removeEventListener("RPC:REQUEST", onRPCRequest);
    rpcBus.removeEventListener("RPC:RESPONSE", onRPCResponse);
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
    if (!target) {
        throw new Error(`No element "${elDescription}" found.`);
    }
    if (elDescription) {
        browser.console.log(`Clicking on: ${elDescription}`);
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
        return Object.keys(calledRPC).length > 0;
    }
    function hasScheduledTask() {
        let size = 0;
        for (const app of App.apps) {
            size += app.scheduler.tasks.size;
        }
        return size > 0;
    }
    function errorDialog() {
        if (document.querySelector(".o_error_dialog")) {
            if (errorRPC) {
                browser.console.error(
                    "A RPC in error was detected, maybe it's related to the error dialog : " +
                        JSON.stringify(errorRPC)
                );
            }
            throw new Error(
                "Error dialog detected" + document.querySelector(".o_error_dialog").innerHTML
            );
        }
        return false;
    }

    while (errorDialog() || !stopCondition() || hasPendingRPC() || hasScheduledTask()) {
        if (state.done) {
            const err = new Error("Clickbot stopped by user");
            err.isUserStop = true;
            throw err;
        }
        if (timeLimit <= 0) {
            let msg = `Timeout, the clicked element took more than ${
                initialTime / 1000
            } seconds to load\n`;
            msg += `Waiting for:\n`;
            if (Object.keys(calledRPC).length > 0) {
                msg += ` * ${Object.values(calledRPC).join(", ")} RPC\n`;
            }
            let scheduleTasks = "";
            for (const app of App.apps) {
                for (const task of app.scheduler.tasks) {
                    scheduleTasks += task.node.name + ",";
                }
            }
            if (scheduleTasks.length > 0) {
                msg += ` * ${scheduleTasks} scheduled tasks\n`;
            }
            if (!stopCondition()) {
                msg += ` * stopCondition: ${stopCondition.toString()}`;
            }
            throw new Error(msg);
        }
        await new Promise((resolve) => setTimeout(resolve, interval));
        timeLimit -= interval;
    }
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
    await triggerClick(studioIcon, "entering studio");
    await waitForCondition(() => document.querySelector(".o_in_studio"));
    await triggerClick(document.querySelector(".o_web_studio_leave"), "leaving studio");
    await waitForCondition(() =>
        document.querySelector(".o_main_navbar:not(.o_studio_navbar) .o_menu_toggle")
    );
    state.studioCount++;
}

/**
 * Test filters
 * Click on each filter in the control panel
 */
async function testFilters() {
    if (state.light === true) {
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
    const filterMenuButton = document.querySelector(".o_dropdown_container.o_filter_menu");
    // Is there a filter menu in the search bar
    if (!filterMenuButton) {
        return;
    }

    // Avoid the "Custom Filter" menu item (it doesn't have the class .o_menu_item)
    const simpleFilterSel = ".o_filter_menu > .dropdown-item.o_menu_item:not(.o_add_custom_filter)";
    const dateFilterSel = ".o_filter_menu > .o_accordion";
    const filterMenuItems = document.querySelectorAll(`${simpleFilterSel},${dateFilterSel}`);
    browser.console.log(`Testing ${filterMenuItems.length} filters`);
    state.testedFilters += filterMenuItems.length;
    for (const filter of filterMenuItems) {
        // Date filters
        if (filter.classList.contains("o_accordion")) {
            await triggerClick(
                filter.querySelector(".o_accordion_toggle"),
                `filter "${filter.innerText.trim()}"`
            );
            // If a filter has options, it will simply unfold and show all options.
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
    if (state.light === true) {
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
        await waitForCondition(
            () => document.querySelector(`.o_switch_view.o_${viewType}.active`) !== null
        );
        await testStudio();
        await testFilters();
    }
}

/**
 * Navigate to a menu via the menu service and test the resulting view.
 *
 * @param {Object} menu menu object from env.services.menu
 * @returns {Promise}
 */
async function testMenuItem(menu) {
    state.currentMenu = menu.name;
    if (BLACKLISTED_MENUS.has(menu.xmlid)) {
        browser.console.log(`Skipping blacklisted menu ${menu.name} (${menu.xmlid})`);
        return;
    }
    browser.console.log(`Testing menu ${menu.name} (${menu.xmlid})`);
    state.testedMenus.push(menu.xmlid);
    const startActionCount = actionCount;
    await env.services.menu.selectMenu(menu);
    try {
        let isModal = false;
        await waitForCondition(() => {
            if (document.querySelector(".o_dialog:not(.o_error_dialog)")) {
                isModal = true;
                browser.console.log(`Modal detected: ${menu.name} (${menu.xmlid})`);
                state.testedModals++;
                return true;
            }
            return startActionCount !== actionCount;
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
        if (!err.isUserStop) {
            browser.console.error(`Error while testing ${menu.name} (${menu.xmlid})`);
        }
        throw err;
    }
}

/**
 * Test an app and all its leaf menus.
 *
 * @param {Object} app app menu object from env.services.menu.getApps()
 * @returns {Promise}
 */
async function testApp(app) {
    browser.console.log(`Testing app: ${app.name} (${app.xmlid})`);
    state.currentApp = app.name;
    if (!state.testedApps.includes(app.xmlid)) {
        state.testedApps.push(app.xmlid);
    }

    if (state.light || !app.children.length) {
        await testMenuItem(app);
        return;
    }

    const flatten = (node) => {
        if (!node.childrenTree?.length) {
            return node.actionID ? [node] : [];
        }
        return node.childrenTree.flatMap(flatten);
    };
    const menus = env.services.menu.getMenuAsTree(app.id).childrenTree.flatMap(flatten);
    state.totalMenus = menus.length;

    while (state.menuIndex < menus.length) {
        await testMenuItem(menus[state.menuIndex]);
        state.menuIndex++;
    }
    state.menuIndex = 0;
    state.totalMenus = 0;
    state.currentMenu = "";
}

/**
 * Main function that starts orchestration of tests
 */
async function _clickEverywhere(xmlId, light, currentState) {
    setup(light, currentState);
    browser.console.log("Starting ClickEverywhere test");
    const startTime = performance.now();
    try {
        if (xmlId) {
            state.xmlId = xmlId;
            const app = env.services.menu.getApps().find((a) => a.xmlid === xmlId);
            if (!app) {
                throw new Error(`No app found for xmlid ${xmlId}`);
            }
            state.currentApp = app.name;
            await testApp(app);
        } else {
            const apps = env.services.menu.getApps();
            state.totalApps = apps.length;
            while (state.appIndex < apps.length) {
                await testApp(apps[state.appIndex]);
                state.appIndex++;
            }
        }

        state.timeTaken = (performance.now() - startTime) / 1000;
        state.done = true;
        browser.console.log(`Test took ${state.timeTaken} seconds`);
        browser.console.log(`Successfully tested ${state.testedApps.length} apps`);
        browser.console.log(`Successfully tested ${state.testedMenus.length} menus`);
        browser.console.log(`Successfully tested ${state.testedModals} modals`);
        browser.console.log(`Successfully tested ${state.testedFilters} filters`);
        if (state.studioCount > 0) {
            browser.console.log(`Successfully tested ${state.studioCount} views in Studio`);
        }
        browser.console.log(SUCCESS_SIGNAL);
    } catch (err) {
        state.timeTaken = (performance.now() - startTime) / 1000;
        if (!err.isUserStop) {
            state.error = err?.message || "test failed";
            state.done = true;
            browser.console.log(`Test took ${state.timeTaken} seconds`);
            browser.console.error(err || "test failed");
        }
    } finally {
        cleanup();
    }
}

function clickEverywhere(xmlId, light = false, currentState) {
    browser.setTimeout(_clickEverywhere, 1000, xmlId, light, currentState);
}

window.clickEverywhere = clickEverywhere;
