// @ts-check
/** @odoo-module native */
/* eslint-disable no-console -- QA automation bot; progress/results output to console is its purpose */

import { App, reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { AppEvent, RpcEvent } from "@web/core/events";
import { rpcBus } from "@web/core/network/rpc";
import { getPopoverForTarget } from "@web/ui/popover";
import {
    clickbotHomeMenuSelectors,
    clickbotSkippedMenus,
    writeClickbotRun,
} from "@web/webclient/clickbot/clickbot_state";

/** @typedef {import("@web/core/network/rpc").RpcEventDetail} RpcEventDetail */

export const SUCCESS_SIGNAL = "clickbot test succeeded";

const MOUSE_EVENTS = ["mouseover", "mouseenter", "mousedown", "mouseup", "click"];
const STUDIO_SYSTRAY_ICON_SELECTOR = ".o_web_studio_navbar_item:not(.o_disabled) i";
const STEP_TIMEOUT = 30000;
const POLL_INTERVAL = 25;

/** @returns {Promise} */
async function waitForNextAnimationFrame() {
    await new Promise(/** @type {any} */ (browser.setTimeout));
    await new Promise((r) => browser.requestAnimationFrame(r));
}

/**
 * @param {EventTarget} target
 * @param {string} elDescription
 * @returns {Promise}
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
        const event = new MouseEvent(type, {
            bubbles: true,
            cancelable: true,
            view: window,
        });
        target.dispatchEvent(event);
    });
    await waitForNextAnimationFrame();
}

/** @returns {number} */
function scheduledTaskCount() {
    let size = 0;
    for (const app of /** @type {any} */ (App).apps) {
        size += app.scheduler.tasks.size;
    }
    return size;
}

/** @returns {string} */
function scheduledTaskNames() {
    const names = [];
    for (const app of /** @type {any} */ (App).apps) {
        for (const task of app.scheduler.tasks) {
            names.push(task.node.name);
        }
    }
    return names.join(",");
}

async function ensureHomeMenu() {
    const homeMenu = document.querySelector("div.o_home_menu");
    if (!homeMenu) {
        let menuToggle = document.querySelector("nav.o_main_navbar > a.o_menu_toggle");
        for (const selector of clickbotHomeMenuSelectors.getAll()) {
            if (menuToggle) {
                break;
            }
            menuToggle = document.querySelector(selector);
        }
        await triggerClick(menuToggle, "home menu toggle button");
    }
}

class ClickBot {
    /**
     * @param {Object} [options]
     * @param {boolean} [options.light]
     * @param {Record<string, any>} [options.currentState]
     */
    constructor({ light = false, currentState } = {}) {
        this.env = /** @type {any} */ (odoo).__WOWL_DEBUG__.root.env;

        /** @type {Record<number, string>} */
        this.calledRPC = {};
        /** @type {Record<string, any> | undefined} */
        this.errorRPC = undefined;
        this.actionCount = 0;
        this.settledCount = 0;
        this._persistQueued = false;
        this._stopped = false;
        /** @type {NodeListOf<Element> | null} */
        this.apps = null;

        this.state = reactive(
            currentState || {
                light,
                startedAt: Date.now(),
                studioCount: 0,
                testedApps: [],
                testedMenus: [],
                testedFilters: 0,
                testedModals: 0,
                appIndex: 0,
                menuIndex: 0,
                subMenuIndex: 0,
            },
            () => this.persist(),
        );

        this.onUiUpdate = () => this.actionCount++;
        this.onActionSettled = () => this.settledCount++;
        this.onRPCRequest = (event) => {
            const detail = /** @type {CustomEvent<RpcEventDetail>} */ (event).detail;
            this.calledRPC[detail.data.id] = detail.url;
        };
        this.onRPCResponse = (event) => {
            const detail = /** @type {CustomEvent<RpcEventDetail>} */ (event).detail;
            if (!detail?.data) {
                return;
            }
            delete this.calledRPC[detail.data.id];
            if (detail.error) {
                this.errorRPC = { ...detail };
            }
        };
    }

    persist() {
        if (this._persistQueued) {
            return;
        }
        this._persistQueued = true;
        Promise.resolve().then(() => {
            this._persistQueued = false;
            this.persistNow();
        });
    }

    persistNow() {
        if (this._stopped) {
            return;
        }
        writeClickbotRun(JSON.stringify(this.state));
    }

    start() {
        const stopButton = document.createElement("button");
        stopButton.setAttribute("id", "stop-clickbot");
        stopButton.classList.add("btn", "btn-danger");
        stopButton.textContent = "Stop ClickAll!";
        stopButton.onclick = () => {
            writeClickbotRun(null);
            browser.location.reload();
        };
        document.body.appendChild(stopButton);

        this.env.bus.addEventListener(
            AppEvent.ACTION_MANAGER_UI_UPDATED,
            this.onUiUpdate,
        );
        this.env.bus.addEventListener(
            AppEvent.ACTION_MANAGER_SETTLED,
            this.onActionSettled,
        );
        rpcBus.addEventListener(RpcEvent.REQUEST, this.onRPCRequest);
        rpcBus.addEventListener(RpcEvent.RESPONSE, this.onRPCResponse);

        this.persistNow();
    }

    stop() {
        this._stopped = true;
        writeClickbotRun(null);
        this.env.bus.removeEventListener(
            AppEvent.ACTION_MANAGER_UI_UPDATED,
            this.onUiUpdate,
        );
        this.env.bus.removeEventListener(
            AppEvent.ACTION_MANAGER_SETTLED,
            this.onActionSettled,
        );
        rpcBus.removeEventListener(RpcEvent.REQUEST, this.onRPCRequest);
        rpcBus.removeEventListener(RpcEvent.RESPONSE, this.onRPCResponse);
        document.getElementById("stop-clickbot")?.remove();
    }

    /**
     * @throws {Error}
     * @returns {boolean}
     */
    checkForErrorDialog() {
        const dialog = document.querySelector(".o_error_dialog");
        if (!dialog) {
            return false;
        }
        if (this.errorRPC) {
            browser.console.error(
                "A RPC in error was detected, maybe it's related to the error dialog : " +
                    JSON.stringify(this.errorRPC),
            );
        }
        throw new Error("Error dialog detected" + dialog.innerHTML);
    }

    /**
     * @param {() => any} stopCondition
     * @returns {Promise}
     */
    async waitForCondition(stopCondition) {
        let timeLimit = STEP_TIMEOUT;
        const pending = () => Object.keys(this.calledRPC);
        for (;;) {
            this.checkForErrorDialog();
            if (
                stopCondition() &&
                pending().length === 0 &&
                scheduledTaskCount() === 0
            ) {
                return;
            }
            if (timeLimit <= 0) {
                let msg = `Timeout, the clicked element took more than ${
                    STEP_TIMEOUT / 1000
                } seconds to load\n`;
                msg += `Waiting for:\n`;
                if (pending().length) {
                    msg += ` * ${Object.values(this.calledRPC).join(", ")} RPC\n`;
                }
                const tasks = scheduledTaskNames();
                if (tasks.length) {
                    msg += ` * ${tasks} scheduled tasks\n`;
                }
                if (!stopCondition()) {
                    msg += ` * stopCondition: ${stopCondition.toString()}`;
                }
                throw new Error(msg);
            }
            await new Promise((resolve) => browser.setTimeout(resolve, POLL_INTERVAL));
            timeLimit -= POLL_INTERVAL;
        }
    }

    async openHomeMenu() {
        await ensureHomeMenu();
        await this.waitForCondition(() => document.querySelector("div.o_home_menu"));
    }

    /** @returns {Promise<Element | undefined>} */
    async getNextMenu() {
        const menuToggles = document.querySelectorAll(
            ".o_menu_sections > .dropdown-toggle, .o_menu_sections > .dropdown-item",
        );
        if (this.state.menuIndex >= menuToggles.length) {
            this.state.menuIndex = 0;
            return;
        }
        let menuToggle = menuToggles[this.state.menuIndex];
        if (menuToggle.classList.contains("dropdown-toggle")) {
            let dropdownMenu = getPopoverForTarget(
                /** @type {HTMLElement} */ (menuToggle),
            );
            if (!dropdownMenu) {
                await triggerClick(menuToggle, "menu toggler");
                dropdownMenu = getPopoverForTarget(
                    /** @type {HTMLElement} */ (menuToggle),
                );
            }
            if (!dropdownMenu) {
                browser.console.error(
                    `Menu toggler "${
                        /** @type {HTMLElement} */ (menuToggle).innerText.trim()
                    }" did not open its dropdown; skipping it.`,
                );
                this.state.menuIndex++;
                this.state.subMenuIndex = 0;
                return this.getNextMenu();
            }
            const items = dropdownMenu.querySelectorAll(".dropdown-item");
            if (this.state.subMenuIndex >= items.length) {
                this.state.menuIndex++;
                this.state.subMenuIndex = 0;
                return;
            }
            menuToggle = items[this.state.subMenuIndex];
            if (this.state.subMenuIndex === items.length - 1) {
                this.state.menuIndex++;
                this.state.subMenuIndex = 0;
            } else {
                this.state.subMenuIndex++;
            }
        } else {
            this.state.menuIndex++;
        }
        return menuToggle;
    }

    /** @returns {Promise<string | undefined>} */
    async getNextApp() {
        if (!this.apps || !this.apps.length) {
            await this.openHomeMenu();
            this.apps = document.querySelectorAll(
                ".o_apps .o_app, .o_pinned_apps .o_app",
            );
        }
        const appName = /** @type {HTMLElement} */ (this.apps[this.state.appIndex])
            ?.dataset?.menuXmlid;
        this.state.appIndex++;
        return appName;
    }

    async testStudio() {
        const studioIcon = document.querySelector(STUDIO_SYSTRAY_ICON_SELECTOR);
        if (!studioIcon) {
            return;
        }
        await triggerClick(studioIcon, "entering studio");
        await this.waitForCondition(() => document.querySelector(".o_in_studio"));
        await triggerClick(
            document.querySelector(".o_web_studio_leave"),
            "leaving studio",
        );
        await this.waitForCondition(() =>
            document.querySelector(
                ".o_main_navbar:not(.o_studio_navbar) .o_menu_toggle",
            ),
        );
        this.state.studioCount++;
    }

    async testFilters() {
        if (this.state.light === true) {
            return;
        }
        const searchBarMenu = document.querySelector(
            ".o_control_panel .dropdown-toggle.o_searchview_dropdown_toggler",
        );
        if (!searchBarMenu) {
            return;
        }
        await triggerClick(searchBarMenu, "search bar menu dropdown");
        const filterMenuButton = document.querySelector(
            ".o_dropdown_container.o_filter_menu",
        );
        if (!filterMenuButton) {
            return;
        }

        const simpleFilterSel =
            ".o_filter_menu > .dropdown-item.o_menu_item:not(.o_add_custom_filter)";
        const dateFilterSel = ".o_filter_menu > .o_accordion";
        const filterMenuItems = document.querySelectorAll(
            `${simpleFilterSel},${dateFilterSel}`,
        );
        browser.console.log(`Testing ${filterMenuItems.length} filters`);
        this.state.testedFilters += filterMenuItems.length;
        for (const filter of filterMenuItems) {
            const label = /** @type {HTMLElement} */ (filter).innerText.trim();
            if (filter.classList.contains("o_accordion")) {
                await triggerClick(
                    filter.querySelector(".o_accordion_toggle"),
                    `filter "${label}"`,
                );

                const firstOption = filter.querySelector(
                    ".o_accordion > .o_accordion_values > .dropdown-item",
                );
                if (firstOption) {
                    await triggerClick(
                        firstOption,
                        `filter option "${/** @type {HTMLElement} */ (firstOption).innerText.trim()}"`,
                    );
                    await this.waitForCondition(() => true);
                }
            } else {
                await triggerClick(filter, `filter "${label}"`);
                await this.waitForCondition(() => true);
            }
        }
    }

    /** @returns {Promise} */
    async testViews() {
        if (this.state.light === true) {
            return;
        }
        const switchButtons = document.querySelectorAll(
            "nav.o_cp_switch_buttons > button.o_switch_view:not(.active):not(.o_map)",
        );
        for (const switchButton of switchButtons) {
            const viewTypeClass = [...switchButton.classList].find(
                (cls) => cls !== "o_switch_view" && cls.startsWith("o_"),
            );
            if (!viewTypeClass) {
                browser.console.warn(
                    "Skipping a view switcher with no o_<viewtype> class:",
                    switchButton.className,
                );
                continue;
            }
            const viewType = viewTypeClass.slice(2);
            browser.console.log(`Testing view switch: ${viewType}`);
            await new Promise((resolve) => browser.setTimeout(resolve, 250));
            const target = document.querySelector(
                `nav.o_cp_switch_buttons > button.o_switch_view.o_${viewType}`,
            );
            if (!target) {
                browser.console.warn(`View switcher for ${viewType} disappeared`);
                continue;
            }
            await triggerClick(target, `${viewType} view switcher`);
            await this.waitForCondition(
                () =>
                    document.querySelector(`.o_switch_view.o_${viewType}.active`) !==
                    null,
            );
            await this.testStudio();
            await this.testFilters();
        }
    }

    /**
     * @param {Element} element
     * @returns {Promise}
     */
    async testMenuItem(element) {
        const el = /** @type {HTMLElement} */ (element);
        const menu = el.dataset.menuXmlid;
        const menuDescription = `${el.innerText.trim()} ${menu}`;
        if (clickbotSkippedMenus.contains(menu)) {
            browser.console.log(`Skipping blacklisted menu ${menuDescription}`);
            return;
        }
        browser.console.log(`Testing menu ${menuDescription}`);
        if (!this.state.testedMenus.includes(menu)) {
            this.state.testedMenus.push(menu);
        }
        const startActionCount = this.actionCount;
        const startSettledCount = this.settledCount;
        await triggerClick(element, `menu item "${el.innerText.trim()}"`);
        try {
            let isModal = false;
            await this.waitForCondition(() => {
                if (
                    !isModal &&
                    document.querySelector(".o_dialog:not(.o_error_dialog)")
                ) {
                    isModal = true;
                    browser.console.log(`Modal detected: ${menuDescription}`);
                    this.state.testedModals++;
                    return true;
                }
                return (
                    isModal ||
                    startActionCount !== this.actionCount ||
                    startSettledCount !== this.settledCount
                );
            });
            if (isModal) {
                await triggerClick(
                    document.querySelector(".o_dialog header > .btn-close"),
                    "modal close button",
                );
            } else {
                await this.testStudio();
                await this.testFilters();
                await this.testViews();
            }
        } catch (err) {
            browser.console.error(`Error while testing ${menuDescription}`);
            throw err;
        }
    }

    /** @returns {Promise} */
    async testApp() {
        if (!this.state.testedApps.includes(this.state.app)) {
            await this.openHomeMenu();
            const element = document.querySelector(
                `a.o_app.o_menuitem[data-menu-xmlid="${this.state.app}"]`,
            );
            if (!element) {
                throw new Error(`No app found for xmlid ${this.state.app}`);
            }
            browser.console.log(`Testing app menu: ${this.state.app}`);
            this.state.testedApps.push(this.state.app);
            await this.testMenuItem(element);
        } else {
            browser.console.log(`already tested app ${this.state.app}`);
        }

        if (this.state.light === true) {
            return;
        }
        let menu = await this.getNextMenu();
        while (menu) {
            await this.testMenuItem(menu);
            menu = await this.getNextMenu();
        }
    }

    report() {
        const { testedApps, testedMenus, testedModals, testedFilters, studioCount } =
            this.state;
        browser.console.log(`Successfully tested ${testedApps.length} apps`);
        browser.console.log(
            `Successfully tested ${testedMenus.length - testedApps.length} menus`,
        );
        browser.console.log(`Successfully tested ${testedModals} modals`);
        browser.console.log(`Successfully tested ${testedFilters} filters`);
        if (studioCount > 0) {
            browser.console.log(`Successfully tested ${studioCount} views in Studio`);
        }
    }

    /**
     * @param {string} [xmlId]
     * @returns {Promise<void>}
     */
    async run(xmlId) {
        this.start();
        console.log("Starting ClickEverywhere test");
        const startTime = performance.now();
        try {
            if (xmlId) {
                this.state.xmlId = xmlId;
                this.state.app = xmlId;
                await this.testApp();
            } else {
                if (this.state.app) {
                    await this.testApp();
                }
                while ((this.state.app = await this.getNextApp())) {
                    this.state.menuIndex = 0;
                    this.state.subMenuIndex = 0;
                    await this.testApp();
                }
            }
            console.log(`Test took ${(performance.now() - startTime) / 1000} seconds`);
            this.report();
            browser.console.log(SUCCESS_SIGNAL);
        } catch (err) {
            console.log(`Test took ${(performance.now() - startTime) / 1000} seconds`);
            browser.console.error(err || "test failed");
        } finally {
            this.stop();
        }
    }
}

/** @type {ClickBot | null} */
let currentRun = null;

/**
 * @param {string} [xmlId]
 * @param {boolean} [light]
 * @param {Record<string, any>} [currentState]
 */
function clickEverywhere(xmlId, light = false, currentState) {
    if (currentRun) {
        browser.console.error("A clickbot run is already in progress; ignoring.");
        return;
    }
    currentRun = /** @type {any} */ ({});
    browser.setTimeout(async () => {
        const bot = new ClickBot({ light, currentState });
        currentRun = bot;
        try {
            await bot.run(xmlId);
        } finally {
            currentRun = null;
        }
    }, 1000);
}

/** @type {any} */ (window).clickEverywhere = clickEverywhere;
