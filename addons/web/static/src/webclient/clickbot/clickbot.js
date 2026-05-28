/**
 * The purpose of this test is to click on every installed App and then open each
 * view. On each view, click on each filter.
 */

import { App, effect, proxy } from "@odoo/owl";
import { rpcBus } from "@web/core/network/rpc";

export const SUCCESS_SIGNAL = "clickbot test succeeded";
export const FAILURE_SIGNAL = "clickbot test failed";

export class ClickbotStopError extends Error {}

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

export class Clickbot {
    constructor(env, { xmlId, light, currentState } = {}) {
        this.env = env;
        this.xmlId = xmlId;
        this.state = proxy(
            currentState || {
                light,
                studioCount: 0,
                testedApps: [],
                testedMenus: [],
                testedFilters: 0,
                testedModals: 0,
                testedViews: 0,
                appIndex: 0,
                menuIndex: 0,
            }
        );
        this._actionCount = 0;
        this._calledRPC = {};
        this._errorRPC = undefined;
        this._disposeEffect = () => {};
    }

    async start() {
        this._setup();
        console.log("Starting ClickEverywhere test");
        this.state.startTime = this.state.startTime || performance.now();
        try {
            if (this.xmlId) {
                this.state.xmlId = this.xmlId;
                const app = this.env.services.menu.getApps().find((a) => a.xmlid === this.xmlId);
                if (!app) {
                    throw new Error(`No app found for xmlid ${this.xmlId}`);
                }
                await this._testApp(app);
            } else {
                const apps = this.env.services.menu.getApps();
                while (this.state.appIndex < apps.length) {
                    await this._testApp(apps[this.state.appIndex]);
                    this.state.appIndex++;
                }
            }

            this._logStatistics();
            console.log(SUCCESS_SIGNAL);
        } catch (err) {
            this._logStatistics();
            if (err instanceof ClickbotStopError) {
                console.log("Clickbot stopped by user");
                console.log(SUCCESS_SIGNAL);
            } else {
                console.error(err);
                console.error(FAILURE_SIGNAL);
            }
        } finally {
            this._cleanup();
        }
    }

    stop() {
        this._stopped = true;
    }

    // ── PRIVATE ─────────────────────────────────────────────

    _createStopButton() {
        const stopButton = document.createElement("button");
        stopButton.setAttribute("id", "stop-clickbot");
        stopButton.classList.add("btn", "btn-danger");
        stopButton.textContent = "Stop ClickAll!";
        stopButton.onclick = () => this.stop();
        document.body.appendChild(stopButton);
    }

    _setup() {
        this._createStopButton();
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", this._uiUpdate);
        rpcBus.addEventListener("RPC:REQUEST", this._onRPCRequest);
        rpcBus.addEventListener("RPC:RESPONSE", this._onRPCResponse);
        this._disposeEffect = effect(() => {
            localStorage.setItem("running.clickbot", JSON.stringify(this.state));
        });
    }

    _cleanup() {
        this._disposeEffect();
        localStorage.removeItem("running.clickbot");
        this.env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", this._uiUpdate);
        rpcBus.removeEventListener("RPC:REQUEST", this._onRPCRequest);
        rpcBus.removeEventListener("RPC:RESPONSE", this._onRPCResponse);
        document.getElementById("stop-clickbot")?.remove();
    }

    _logStatistics() {
        console.log(`Test took ${(performance.now() - this.state.startTime) / 1000} seconds`);
        console.log(`Successfully tested ${this.state.testedApps.length} apps`);
        console.log(`Successfully tested ${this.state.testedMenus.length} menus`);
        console.log(`Successfully tested ${this.state.testedViews} views`);
        console.log(`Successfully tested ${this.state.testedModals} modals`);
        console.log(`Successfully tested ${this.state.testedFilters} filters`);
        if (this.state.studioCount > 0) {
            console.log(`Successfully tested ${this.state.studioCount} views in Studio`);
        }
    }
    _onRPCRequest = ({ detail }) => {
        this._calledRPC[detail.data.id] = detail.url;
    };

    _onRPCResponse = ({ detail }) => {
        delete this._calledRPC[detail.data.id];
        if (detail.error) {
            this._errorRPC = { ...detail };
        }
    };

    _uiUpdate = () => {
        this._actionCount++;
    };

    async _waitForNextAnimationFrame() {
        await new Promise(setTimeout);
        await new Promise((r) => requestAnimationFrame(r));
    }

    async _triggerClick(target, elDescription) {
        if (!target) {
            throw new Error(`No element "${elDescription}" found.`);
        }
        if (elDescription) {
            console.log(`Clicking on: ${elDescription}`);
        }
        MOUSE_EVENTS.forEach((type) => {
            const event = new MouseEvent(type, { bubbles: true, cancelable: true, view: window });
            target.dispatchEvent(event);
        });
        await this._waitForNextAnimationFrame();
    }

    async _waitForCondition(stopCondition) {
        const interval = 25;
        const initialTime = 30000;
        let timeLimit = initialTime;

        const hasPendingRPC = () => Object.keys(this._calledRPC).length > 0;
        const hasScheduledTask = () => {
            let size = 0;
            for (const app of App.apps) {
                size += app.scheduler.tasks.size;
            }
            return size > 0;
        };
        const errorDialog = () => {
            if (document.querySelector(".o_error_dialog")) {
                if (this._errorRPC) {
                    console.error(
                        "A RPC in error was detected, maybe it's related to the error dialog : " +
                            JSON.stringify(this._errorRPC)
                    );
                }
                throw new Error(
                    "Error dialog detected" + document.querySelector(".o_error_dialog").innerHTML
                );
            }
            return false;
        };

        while (errorDialog() || !stopCondition() || hasPendingRPC() || hasScheduledTask()) {
            if (this._stopped) {
                throw new ClickbotStopError("Clickbot stopped by user");
            }
            if (timeLimit <= 0) {
                let msg = `Timeout, the clicked element took more than ${
                    initialTime / 1000
                } seconds to load\n`;
                msg += `Waiting for:\n`;
                if (Object.keys(this._calledRPC).length > 0) {
                    msg += ` * ${Object.values(this._calledRPC).join(", ")} RPC\n`;
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
                    msg += ` * stopCondition: ${stopCondition.toString()}\n`;
                }
                msg += ` on testing menu ${this.currentMenu.name} (${this.currentMenu.xmlid})`;
                throw new Error(msg);
            }
            await new Promise((resolve) => setTimeout(resolve, interval));
            timeLimit -= interval;
        }
    }

    async _testStudio() {
        const studioIcon = document.querySelector(STUDIO_SYSTRAY_ICON_SELECTOR);
        if (!studioIcon) {
            return;
        }
        await this._triggerClick(studioIcon, "entering studio");
        await this._waitForCondition(() => document.querySelector(".o_in_studio"));
        await this._triggerClick(document.querySelector(".o_web_studio_leave"), "leaving studio");
        await this._waitForCondition(() =>
            document.querySelector(".o_main_navbar:not(.o_studio_navbar) .o_menu_toggle")
        );
        this.state.studioCount++;
    }

    async _testFilters() {
        if (this.state.light === true) {
            return;
        }
        const searchBarMenu = document.querySelector(
            ".o_control_panel .dropdown-toggle.o_searchview_dropdown_toggler"
        );
        if (!searchBarMenu) {
            return;
        }
        await this._triggerClick(searchBarMenu);
        const filterMenuButton = document.querySelector(".o_dropdown_container.o_filter_menu");
        if (!filterMenuButton) {
            return;
        }

        // Avoid the "Custom Filter" menu item (it doesn't have the class .o_menu_item)
        const simpleFilterSel =
            ".o_filter_menu > .dropdown-item.o_menu_item:not(.o_add_custom_filter)";
        const dateFilterSel = ".o_filter_menu > .o_accordion";
        const filterMenuItems = document.querySelectorAll(`${simpleFilterSel},${dateFilterSel}`);
        console.log(`Testing ${filterMenuItems.length} filters`);
        this.state.testedFilters += filterMenuItems.length;
        for (const filter of filterMenuItems) {
            if (filter.classList.contains("o_accordion")) {
                await this._triggerClick(
                    filter.querySelector(".o_accordion_toggle"),
                    `filter "${filter.innerText.trim()}"`
                );
                // If a filter has options, it will simply unfold and show all options.
                // We then click on the first one.
                const firstOption = filter.querySelector(
                    ".o_accordion > .o_accordion_values > .dropdown-item"
                );
                if (firstOption) {
                    await this._triggerClick(
                        firstOption,
                        `filter option "${firstOption.innerText.trim()}"`
                    );
                    await this._waitForCondition(() => true);
                }
            } else {
                await this._triggerClick(filter, `filter "${filter.innerText.trim()}"`);
                await this._waitForCondition(() => true);
            }
        }
    }

    async _testView() {
        await this._testStudio();
        await this._testFilters();
    }

    async _testViews() {
        await this._testView();
        this.state.testedViews++;
        if (this.state.light === true) {
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
            console.log(`Testing view switch: ${viewType}`);
            // timeout to avoid click debounce
            setTimeout(() => {
                const target = document.querySelector(
                    `nav.o_cp_switch_buttons > button.o_switch_view.o_${viewType}`
                );
                if (target) {
                    this._triggerClick(target, `${viewType} view switcher`);
                }
            }, 250);
            await this._waitForCondition(
                () => document.querySelector(`.o_switch_view.o_${viewType}.active`) !== null
            );
            await this._testView();
            this.state.testedViews++;
        }
    }

    async _testMenuItem(menu) {
        this.currentMenu = menu;
        if (BLACKLISTED_MENUS.has(menu.xmlid)) {
            console.log(`Skipping blacklisted menu ${menu.name} (${menu.xmlid})`);
            return;
        }
        console.log(`Testing menu ${menu.name} (${menu.xmlid})`);
        this.state.testedMenus.push(menu.xmlid);
        const startActionCount = this._actionCount;
        await this.env.services.menu.selectMenu(menu);
        try {
            let isModal = false;
            await this._waitForCondition(() => {
                if (document.querySelector(".o_dialog:not(.o_error_dialog)")) {
                    isModal = true;
                    console.log(`Modal detected: ${menu.name} (${menu.xmlid})`);
                    this.state.testedModals++;
                    return true;
                }
                return startActionCount !== this._actionCount;
            });
            if (isModal) {
                await this._triggerClick(
                    document.querySelector(".o_dialog header > .btn-close"),
                    "modal close button"
                );
            } else {
                await this._testViews();
            }
        } catch (err) {
            console.error(`Error while testing ${menu.name} (${menu.xmlid})`);
            throw err;
        }
    }

    async _testApp(app) {
        console.log(`Testing app: ${app.name} (${app.xmlid})`);
        if (!this.state.testedApps.includes(app.xmlid)) {
            this.state.testedApps.push(app.xmlid);
        }

        if (this.state.light || !app.children.length) {
            await this._testMenuItem(app);
            return;
        }

        const flatten = (node) => {
            if (!node.childrenTree?.length) {
                return node.actionID ? [node] : [];
            }
            return node.childrenTree.flatMap(flatten);
        };
        const menus = this.env.services.menu.getMenuAsTree(app.id).childrenTree.flatMap(flatten);

        while (this.state.menuIndex < menus.length) {
            await this._testMenuItem(menus[this.state.menuIndex]);
            this.state.menuIndex++;
        }
        this.state.menuIndex = 0;
    }
}
