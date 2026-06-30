/**
 * The purpose of this test is to click on every installed App and then open each
 * view. On each view, click on each filter.
 */

import { App, effect, proxy } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpcBus } from "@web/core/network/rpc";
import { ClickbotOverlay } from "@web/webclient/clickbot/clickbot_overlay";

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
    "website_sale.menu_open_shop", // menu that opens a website editor
]);

const BLACKLISTED_NEW_RECORD = new Set([
    "website_hr_recruitment.menu_job_pages", // The new button opens a website editor, not a form
    "stock.menu_action_warehouse_form", // It opens an error dialog : Creating a new warehouse will automatically activate the Storage Locations setting.
]);

const BLACKLISTED_OFFLINE_MENUS = new Set([
    "mass_mailing.mass_mailing_menu_root", // form view hangs offline loading iframe assets
    "mass_mailing_sms.mass_mailing_sms_menu_root", // form view hangs offline loading iframe assets
]);

const BLACKLISTED_RECORD_ACTIONS = new Set([
    "website.menu_website_pages_list", // list/kanban opens the website in website editor not a form
    "website.menu_website_technical_pages", // list/kanban opens the website in website editor not a form
    "test_website.menu_test_website_test_model", // list opens the website in website editor not a form
    "data_cleaning.ir_model_menu_merge_action_manager", // list that checks a checkbox in the list
    "knowledge.knowledge_menu_article", // list/kanban that opens knowledge articles, in a knowledge article we dont have the breadcrumb and can't go back
    "sign.sign_template_menu", // opens sign in a iframe.
    "sign.sign_request_my_documents", // opens sign in a iframe.
    "sign.sign_request_documents", // opens sign in a iframe.
    "documents.dashboard", // there is no form view
    "spreadsheet_dashboard.spreadsheet_dashboard_group_menu_configuration_sections", // there is no form view
    "website.menu_visitor_view_menu", // there is no form view
]);

// Actions that don't open a form view when clicking on list/kanban
const EXCEPTION_RECORD_ACTIONS = {
    "mail.menu_channel": {
        list: {
            toCheck: ".o-mail-ChatWindow",
            toGoBack: ".o-mail-ChatWindow .o-mail-ActionList-button[name=close]",
        },
        kanban: {
            toCheck: ".o-mail-ChatWindow",
            toGoBack: ".o-mail-ChatWindow .o-mail-ActionList-button[name=close]",
        },
    },
    "mail.discuss_channel_menu_settings": {
        list: {
            toCheck: ".o-mail-ChatWindow",
            toGoBack: ".o-mail-ChatWindow .o-mail-ActionList-button[name=close]",
        },
        kanban: {
            toCheck: ".o-mail-ChatWindow",
            toGoBack: ".o-mail-ChatWindow .o-mail-ActionList-button[name=close]",
        },
    },
    "crm.sales_team_menu_team_pipeline": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "sale.report_sales_team": {
        kanban: {
            toCheck: ".o_graph_view",
            toGoBack: ".o_back_button",
        },
    },
    "ai_app.ai_agent_menu_action": {
        kanban: {
            toCheck: ".o-mail-ChatWindow",
            toGoBack: ".o-mail-ChatWindow .o-mail-ActionList-button[name=close]",
        },
    },
    "ai_app.ai_menu_root": {
        kanban: {
            toCheck: ".o-mail-ChatWindow",
            toGoBack: ".o-mail-ChatWindow .o-mail-ActionList-button[name=close]",
        },
    },
    "project.menu_projects": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "project.menu_main_pm": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "helpdesk.helpdesk_menu_team_dashboard": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "helpdesk.menu_helpdesk_root": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "mass_mailing.menu_email_mass_mailing_lists": {
        kanban: {
            toCheck: ".o_list_view",
            toGoBack: ".o_back_button",
        },
    },
    "mass_mailing_sms.mailing_list_menu_sms": {
        kanban: {
            toCheck: ".o_list_view",
            toGoBack: ".o_back_button",
        },
    },
    "im_livechat.support_channels": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "im_livechat.menu_livechat_root": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "fleet.fleet_vehicle_model_brand_menu": {
        kanban: {
            toCheck: ".o_list_view",
            toGoBack: ".o_back_button",
        },
    },
    "appointment.main_menu_appointments": {
        kanban: {
            toCheck: ".o_gantt_view",
            toGoBack: ".o_back_button",
        },
    },
    "frontdesk.frontdesk_menu_root": {
        kanban: {
            toCheck: ".o_list_view",
            toGoBack: ".o_back_button",
        },
    },
    "hr_recruitment.menu_hr_recruitment_root": {
        kanban: {
            toCheck: ".o_kanban_view",
            toGoBack: ".o_back_button",
        },
    },
    "equity.menu_equity": {
        kanban: {
            toCheck: ".o_list_renderer",
            toGoBack: ".o_back_button",
        },
    },
    "lunch.menu_lunch": {
        kanban: {
            toCheck: ".o_dialog",
            toGoBack: ".o_dialog .btn-close",
        },
        list: {
            toCheck: ".o_dialog",
            toGoBack: ".o_dialog .btn-close",
        },
    },
};

// If you change this selector, adapt Studio test "Studio icon matches the clickbot selector"
const STUDIO_SYSTRAY_ICON_SELECTOR = ".o_web_studio_navbar_item:not(.o_disabled) i";

// State (including xmlId) is always built and owned by ClickbotLauncher (below);
// Clickbot never constructs its own default state.
class Clickbot {
    constructor(env, currentState) {
        this.env = env;
        this.state = proxy(currentState);
        this._actionCount = 0;
        this._calledRPC = {};
        this._errorRPC = undefined;
        this._disposeEffect = () => {};
    }

    get _stats() {
        return this.state.testingOffline ? this.state.offlineStats : this.state.onlineStats;
    }

    _isMenuAvailableOffline(menu) {
        return (
            !this.state.testingOffline ||
            !menu.actionID ||
            this.env.services.offline.isAvailableOffline(menu.actionID)
        );
    }

    async start() {
        this._setup();
        if (this.state.logger) {
            console.log("Starting ClickEverywhere test");
        }
        this.state.startTime = this.state.startTime || performance.now();
        this.state.phase = "running";
        if (!this.state.xmlId) {
            this.state.totalApps = this.env.services.menu.getApps().length;
        }
        try {
            if (!this.state.testingOffline) {
                await this._start();
            }

            if (this.state.offline) {
                await this._testOffline();
            }

            this._logStatistics();
            const totalErrors =
                this.state.onlineStats.errorMenuCount +
                (this.state.offline ? this.state.offlineStats.errorMenuCount : 0);
            if (totalErrors === 0) {
                console.log(SUCCESS_SIGNAL);
            } else {
                this._originalError(FAILURE_SIGNAL);
            }
        } catch (err) {
            this._logStatistics();
            if (err instanceof ClickbotStopError) {
                console.log("Clickbot stopped by user");
                console.log(SUCCESS_SIGNAL);
            } else {
                this.state.error = err.message || String(err);
                this._originalError(err);
                this._originalError(FAILURE_SIGNAL);
            }
        } finally {
            this._cleanup();
            this.state.timeTaken = (performance.now() - this.state.startTime) / 1000;
            this.state.phase = "done";
        }
    }

    stop() {
        this._stopped = true;
    }

    // ── PRIVATE ─────────────────────────────────────────────

    async _start() {
        if (this.state.xmlId) {
            const app = this.env.services.menu.getApps().find((a) => a.xmlid === this.state.xmlId);
            if (!app) {
                throw new Error(`No app found for xmlid ${this.state.xmlId}`);
            }
            this.currentAPP = app;
            await this._testApp(app);
        } else {
            this.state.appIndex = 0;
            const apps = this.env.services.menu.getApps();
            while (this.state.appIndex < apps.length) {
                this.currentAPP = apps[this.state.appIndex];
                await this._testApp(apps[this.state.appIndex]);
                this.state.appIndex++;
            }
        }
    }

    async _testOffline() {
        if (this.state.logger) {
            console.log("Start testing offline");
        }
        this.state.testingOffline = true;

        class FakeOfflineXHR extends EventTarget {
            open() {}
            setRequestHeader() {}
            send() {
                setTimeout(() => this.dispatchEvent(new ProgressEvent("error")), 20);
            }
        }

        this.oldFetch = window.fetch;
        this.originalXHR = window.XMLHttpRequest;

        const rejectFetch = () => Promise.reject(new TypeError("Failed to fetch"));
        browser.fetch = rejectFetch;
        window.fetch = rejectFetch;
        browser.XMLHttpRequest = FakeOfflineXHR;
        window.XMLHttpRequest = FakeOfflineXHR;

        this.env.services.offline.offline = true;
        await this.env.services.offline.getVisitedStatus();

        return this._start();
    }

    _setup() {
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", this._uiUpdate);
        rpcBus.addEventListener("RPC:REQUEST", this._onRPCRequest);
        rpcBus.addEventListener("RPC:RESPONSE", this._onRPCResponse);
        this._disposeEffect = effect(() => {
            localStorage.setItem("running.clickbot", JSON.stringify(this.state));
        });
        this._originalWarn = console.warn;
        console.warn = (...args) => {
            let msg = `Warning detected:\n`;
            msg += this._currentTraceback();
            msg += `The warning is :\n`;
            msg += args;
            this._originalWarn(msg);
        };
        this._originalError = console.error;
        console.error = (...args) => {
            let msg = `Error detected:\n`;
            msg += this._currentTraceback();
            msg += `The error is :\n`;
            msg += args;
            this._originalError(msg);
        };
    }

    _cleanup() {
        this._disposeEffect();
        if (this.oldFetch) {
            browser.fetch = this.oldFetch;
            browser.XMLHttpRequest = this.originalXHR;
            window.fetch = this.oldFetch;
            window.XMLHttpRequest = this.originalXHR;
            this.env.services.offline.offline = false;
        }
        console.warn = this._originalWarn;
        console.error = this._originalError;
        localStorage.removeItem("running.clickbot");
        this.env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", this._uiUpdate);
        rpcBus.removeEventListener("RPC:REQUEST", this._onRPCRequest);
        rpcBus.removeEventListener("RPC:RESPONSE", this._onRPCResponse);
    }

    _logStatistics() {
        if (!this.state.logger) {
            return;
        }
        console.log(`Test took ${(performance.now() - this.state.startTime) / 1000} seconds`);
        this._logStats(this.state.onlineStats);
        if (this.state.offline) {
            console.log(`---- Offline stats ----`);
            this._logStats(this.state.offlineStats);
        }
    }

    _logStats(stats) {
        console.log(`Tested ${stats.testedApps.length} apps`);
        console.log(`Tested ${stats.testedMenus.length} menus`);
        if (stats.errorMenuCount > 0) {
            console.log(`Error found while testing ${stats.errorMenuCount} menus`);
        }
        console.log(`Tested ${stats.testedViews} views`);
        console.log(`Tested ${stats.testedFormsViews} form views`);
        console.log(`Tested ${stats.testedNewRecord} new record views`);
        console.log(`Tested ${stats.testedModals} modals`);
        if (stats.testedFilters !== undefined) {
            console.log(`Tested ${stats.testedFilters} filters`);
        }
        if (stats.studioCount) {
            console.log(`Tested ${stats.studioCount} views in Studio`);
        }
    }

    _currentTraceback() {
        let msg = ` - Current testing app is ${this.currentAPP.name} (${this.currentAPP.xmlid})\n`;
        msg += ` - Current testing menu is ${this.currentMenu.name} (${this.currentMenu.xmlid})\n`;
        if (this.currentView) {
            msg += ` - Current testing view is ${this.currentView}\n`;
        }
        if (this.currentFilter) {
            msg += ` - Current testing filter is ${this.currentFilter}\n`;
        }
        if (this.state.testingOffline) {
            msg += ` - Currently running offline\n`;
        }
        return msg;
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

    async _waitForCondition(stopCondition, message) {
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
                let msg = `Error dialog detected when waiting for ${message} : ${
                    document.querySelector(".o_error_dialog").innerHTML
                }`;
                if (this._errorRPC) {
                    msg += `\nA RPC in error was detected, maybe it's related to the error dialog : ${JSON.stringify(
                        this._errorRPC
                    )}`;
                }

                // Close the error dialog
                // TODO: Not sure if this is needed.
                document.querySelector(".o_dialog header > .btn-close").click();

                throw new Error(msg);
            }
            return false;
        };

        while (errorDialog() || !stopCondition() || hasPendingRPC() || hasScheduledTask()) {
            if (this._stopped) {
                throw new ClickbotStopError("Clickbot stopped by user");
            }
            if (timeLimit <= 0) {
                let msg = `Timeout when: ${message}, it took more than ${
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
                throw new Error(msg);
            }
            await new Promise((resolve) => setTimeout(resolve, interval));
            timeLimit -= interval;
        }
    }

    async _triggerClick(target, stopCondition, elDescription) {
        if (!target) {
            throw new Error(`No element "${elDescription}" found.`);
        }
        if (elDescription && this.state.logger) {
            console.log(`Clicking on: ${elDescription}`);
        }
        MOUSE_EVENTS.forEach((type) => {
            const event = new MouseEvent(type, { bubbles: true, cancelable: true, view: window });
            target.dispatchEvent(event);
        });
        await this._waitForNextAnimationFrame();
        await this._waitForCondition(stopCondition, `clicking on ${elDescription}`);
    }

    async _testStudio() {
        const studioIcon = document.querySelector(STUDIO_SYSTRAY_ICON_SELECTOR);
        if (!studioIcon) {
            return;
        }
        await this._triggerClick(
            studioIcon,
            () => document.querySelector(".o_in_studio"),
            "entering studio"
        );
        await this._triggerClick(
            document.querySelector(".o_web_studio_leave"),
            () => document.querySelector(".o_main_navbar:not(.o_studio_navbar) .o_menu_toggle"),
            "leaving studio"
        );
        this._stats.studioCount++;
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
        await this._triggerClick(searchBarMenu, () => true);
        const filterMenuButton = document.querySelector(".o_dropdown_container.o_filter_menu");
        if (!filterMenuButton) {
            return;
        }

        // Avoid the "Custom Filter" menu item (it doesn't have the class .o_menu_item)
        const simpleFilterSel =
            ".o_filter_menu > .dropdown-item.o_menu_item:not(.o_add_custom_filter)";
        const dateFilterSel = ".o_filter_menu > .o_accordion";
        const filterMenuItems = document.querySelectorAll(`${simpleFilterSel},${dateFilterSel}`);
        if (this.state.logger) {
            console.log(`Testing ${filterMenuItems.length} filters`);
        }
        this._stats.testedFilters += filterMenuItems.length;
        for (const filter of filterMenuItems) {
            if (filter.classList.contains("o_accordion")) {
                this.currentFilter = filter.innerText.trim();
                await this._triggerClick(
                    filter.querySelector(".o_accordion_toggle"),
                    () => true,
                    `filter "${this.currentFilter}"`
                );
                // If a filter has options, it will simply unfold and show all options.
                // We then click on the first one.
                const firstOption = filter.querySelector(
                    ".o_accordion > .o_accordion_values > .dropdown-item"
                );
                if (firstOption) {
                    this.currentFilter = `${this.currentFilter} (${firstOption.innerText.trim()})`;
                    await this._triggerClick(
                        firstOption,
                        () => true,
                        `filter "${this.currentFilter}"`
                    );
                    await this._testClickingRecord();
                }
            } else {
                this.currentFilter = filter.innerText.trim();
                await this._triggerClick(filter, () => true, `filter "${this.currentFilter}"`);
                await this._testClickingRecord();
            }
        }
        this.currentFilter = undefined;
    }

    /**
     * Test clicking on a record in list or kanban view
     * @returns {Promise}
     */

    async _testClickingRecord() {
        if (BLACKLISTED_RECORD_ACTIONS.has(this.currentMenu.xmlid)) {
            if (this.state.logger) {
                console.log(
                    `Skipping blacklisted form menu ${this.currentMenu.name} (${this.currentMenu.xmlid})`
                );
            }
            return;
        }

        if (this.recordTested) {
            return;
        }
        const exceptionActions = EXCEPTION_RECORD_ACTIONS[this.currentMenu.xmlid];

        if (document.querySelector(".o_list_view")) {
            if (this.formviewTested && !exceptionActions?.list) {
                return;
            }
            const records = document.querySelector(".o_view_sample_data")
                ? false
                : Boolean(document.querySelector("tr.o_data_row td.o_data_cell.cursor-pointer"));
            if (records) {
                this.recordTested = true;
                const row = document.querySelectorAll(".o_data_row")[0];
                if (row.classList.contains("o_disabled_offline")) {
                    return;
                }
                // Open the first record in the list
                const stopCondition = exceptionActions?.list?.toCheck
                    ? () => document.querySelector(exceptionActions?.list?.toCheck) !== null
                    : () =>
                          document.querySelector(".o_form_view") !== null ||
                          document.querySelector(".o_data_row.o_selected_row") !== null;

                if (document.querySelector(".o_list_record_open_form_view")) {
                    await this._triggerClick(
                        row.querySelector(".o_list_record_open_form_view"),
                        stopCondition,
                        "open form view from list (View Button)"
                    );
                } else {
                    await this._triggerClick(
                        row.querySelector(".o_data_cell"),
                        stopCondition,
                        "open form view from list"
                    );
                }

                // Go back to the list
                if (exceptionActions?.list?.toGoBack) {
                    await this._triggerClick(
                        document.querySelector(exceptionActions?.list?.toGoBack),
                        () => document.querySelector(`.o_list_view`) !== null,
                        "go back to list view (from special record view)"
                    );
                } else if (document.querySelector(".o_form_view")) {
                    this.formviewTested = true;
                    this._stats.testedFormsViews++;
                    await this._triggerClick(
                        document.querySelector(".o_back_button"),
                        () => document.querySelector(`.o_list_view`) !== null,
                        "go back to list view (from record view)"
                    );
                } else {
                    await this._triggerClick(
                        document.querySelector(".o_list_button_discard"),
                        () => document.querySelector(`.o_list_view`) !== null,
                        "discard the editable list"
                    );
                }
            }
        } else if (document.querySelector(".o_kanban_view")) {
            if (this.formviewTested && !exceptionActions?.kanban) {
                return;
            }
            const records = document.querySelector(".o_view_sample_data")
                ? false
                : Boolean(
                      document.querySelectorAll(
                          ".o_kanban_record:not(.o_kanban_ghost).cursor-pointer"
                      ).length
                  );
            if (records) {
                this.recordTested = true;
                const card = document.querySelectorAll(
                    ".o_kanban_record:not(.o_kanban_ghost).cursor-pointer"
                )[0];
                if (card.classList.contains("o_disabled_offline")) {
                    return;
                }
                const stopCondition = exceptionActions?.kanban?.toCheck
                    ? () => document.querySelector(exceptionActions?.kanban?.toCheck) !== null
                    : () => document.querySelector(".o_form_view") !== null;
                // Open the first record in the kanban
                await this._triggerClick(card, stopCondition, "open form view from kanban");

                // Go back to the kanban
                if (exceptionActions?.kanban?.toGoBack) {
                    await this._triggerClick(
                        document.querySelector(exceptionActions?.kanban?.toGoBack),
                        () => document.querySelector(`.o_kanban_view`) !== null,
                        "go back to kanban view (from special record view)"
                    );
                } else {
                    // form view
                    this.formviewTested = true;
                    this._stats.testedFormsViews++;
                    await this._triggerClick(
                        document.querySelector(".o_back_button"),
                        () => document.querySelector(`.o_kanban_view`) !== null,
                        "go back to kanban view (from record view)"
                    );
                }
            }
        }
    }

    async _testNewRecord() {
        if (BLACKLISTED_NEW_RECORD.has(this.currentMenu.xmlid)) {
            if (this.state.logger) {
                console.log(
                    `Skipping blacklisted new record menu ${this.currentMenu.name} (${this.currentMenu.xmlid})`
                );
            }
            return;
        }
        if (
            document.querySelector(".o_list_view") &&
            document.querySelector(".o_list_button_add:not(.dropdown)")
        ) {
            const listNewBtn = document.querySelector(".o_list_button_add");
            if (listNewBtn.classList.contains("o_disabled_offline")) {
                return;
            }
            await this._triggerClick(
                listNewBtn,
                () =>
                    document.querySelector(".o_form_view") !== null ||
                    document.querySelector(".o_data_row.o_selected_row") !== null ||
                    document.querySelector(".o_dialog:not(.o_error_dialog)") !== null,
                "list view's new button"
            );

            this._stats.testedNewRecord++;

            // close the modal
            if (document.querySelector(".o_dialog:not(.o_error_dialog)")) {
                return this._triggerClick(
                    document.querySelector(".o_dialog header > .btn-close"),
                    () => document.querySelector(".o_dialog") === null,
                    "modal close button"
                );
            }
            // Go back to the list
            if (document.querySelector(".o_form_view")) {
                return this._triggerClick(
                    document.querySelector(".o_back_button"),
                    () => document.querySelector(`.o_list_view`) !== null,
                    "go back to list view (from new record form view)"
                );
            }
            if (document.querySelector(".o_data_row.o_selected_row")) {
                return this._triggerClick(
                    document.querySelector(".o_list_button_discard"),
                    () => document.querySelector(`.o_list_view`) !== null,
                    "discard the editable list (from new record, editable list)"
                );
            }
            throw new Error("Could not find a way to go back to the list view");
        } else if (
            document.querySelector(".o_kanban_view") &&
            document.querySelector(".o-kanban-button-new:not(.dropdown)")
        ) {
            const kanbanNewBtn = document.querySelector(".o-kanban-button-new");
            if (kanbanNewBtn.classList.contains("o_disabled_offline")) {
                return;
            }
            await this._triggerClick(
                kanbanNewBtn,
                () =>
                    document.querySelector(".o_form_view") !== null ||
                    document.querySelector(".o_kanban_quick_create") !== null ||
                    document.querySelector(".o_dialog:not(.o_error_dialog)") !== null,
                "kanban view's new button"
            );

            this._stats.testedNewRecord++;

            // close the modal
            if (document.querySelector(".o_dialog:not(.o_error_dialog)")) {
                return this._triggerClick(
                    document.querySelector(".o_dialog header > .btn-close"),
                    () => document.querySelector(".o_dialog") === null,
                    "modal close button"
                );
            }
            // Go back to the kanban
            if (document.querySelector(".o_kanban_quick_create_form")) {
                return this._triggerClick(
                    document.querySelector(".o_kanban_cancel"),
                    () => document.querySelector(`.o_kanban_view`) !== null,
                    "discard the kanban (from kanban quick create form)"
                );
            }
            if (document.querySelector(".o_form_view")) {
                return this._triggerClick(
                    document.querySelector(".o_back_button"),
                    () => document.querySelector(`.o_kanban_view`) !== null,
                    "go back to kanban view (from new record form view)"
                );
            }
            throw new Error("Could not find a way to go back to the kanban view");
        }
    }

    async _testView(viewType) {
        this.currentView = viewType;
        this.recordTested = false;
        await this._testNewRecord();
        await this._testClickingRecord();
        if (!this.state.offline) {
            await this._testStudio();
            await this._testFilters();
        }
        this.currentView = undefined;
    }

    async _testViews() {
        this.formviewTested = false;
        let viewType;
        if (document.querySelector(".o_view_controller")) {
            viewType = [...document.querySelector(".o_view_controller").classList]
                .find((c) => c.startsWith(`o_`) && c.endsWith(`_view`))
                .split("_")[1];
        }
        await this._testView(viewType);
        this._stats.testedViews++;
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
            if (this.state.logger) {
                console.log(`Testing view switch: ${viewType}`);
            }
            // timeout to avoid click debounce
            const target = document.querySelector(
                `nav.o_cp_switch_buttons > button.o_switch_view.o_${viewType}`
            );
            if (target && !target.classList.contains("o_disabled_offline")) {
                await this._triggerClick(
                    target,
                    () => document.querySelector(`.o_switch_view.o_${viewType}.active`) !== null,
                    `${viewType} view switcher`
                );
                await this._testView(viewType);
                this._stats.testedViews++;
            }
        }
    }

    async _testMenuItem(menu) {
        this.currentMenu = menu;
        if (BLACKLISTED_MENUS.has(menu.xmlid)) {
            if (this.state.logger) {
                console.log(`Skipping blacklisted menu ${menu.name} (${menu.xmlid})`);
            }
            return;
        }
        if (this.state.testingOffline && BLACKLISTED_OFFLINE_MENUS.has(menu.xmlid)) {
            if (this.state.logger) {
                console.log(`Skipping offline-blacklisted menu ${menu.name} (${menu.xmlid})`);
            }
            return;
        }
        if (!this._isMenuAvailableOffline(menu)) {
            if (this.state.logger) {
                console.log(`Skipping offline-unavailable menu ${menu.name} (${menu.xmlid})`);
            }
            return;
        }
        if (this.state.logger) {
            console.log(`Testing menu ${menu.name} (${menu.xmlid})`);
        }
        this._stats.testedMenus.push(menu.xmlid);
        const startActionCount = this._actionCount;
        try {
            await this.env.services.menu.selectMenu(menu);
            let isModal = false;
            await this._waitForCondition(() => {
                if (document.querySelector(".o_dialog:not(.o_error_dialog)")) {
                    isModal = true;
                    if (this.state.logger) {
                        console.log(`Modal detected: ${menu.name} (${menu.xmlid})`);
                    }
                    this._stats.testedModals++;
                    return true;
                }
                return startActionCount !== this._actionCount;
            }, `selecting menu ${menu.name} (${menu.xmlid})`);
            if (isModal) {
                await this._triggerClick(
                    document.querySelector(".o_dialog header > .btn-close"),
                    () => document.querySelector(".o_dialog") === null,
                    "modal close button"
                );
            } else {
                await this._testViews();
            }
        } catch (err) {
            if (err instanceof ClickbotStopError) {
                throw err;
            }
            this._stats.errorMenuCount++;
            let msg = `Error found:\n`;
            msg += this._currentTraceback();
            msg += `The error is :\n`;
            msg += err.message;
            this._originalError(msg);
        }
    }

    async _testApp(app) {
        this.state.currentApp = app.name;
        if (this.state.logger) {
            console.log(`Testing app: ${app.name} (${app.xmlid})`);
        }
        if (!this._stats.testedApps.includes(app.xmlid)) {
            this._stats.testedApps.push(app.xmlid);
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

        this.state.totalMenus = menus.length;
        while (this.state.menuIndex < menus.length) {
            await this._testMenuItem(menus[this.state.menuIndex]);
            this.state.menuIndex++;
        }
        this.state.menuIndex = 0;
    }
}

// Drives the overlay UI: owns the one state object shared verbatim with Clickbot
// and with ClickbotOverlay, and (re)creates the Clickbot instance on start().
export class ClickbotLauncher {
    constructor(env, persistedState) {
        this.env = env;
        this.apps = env.services.menu.getApps();
        this.state = proxy({
            light: false,
            logger: true,
            offline: false,
            testingOffline: false,
            appIndex: 0,
            menuIndex: 0,
            currentApp: "",
            totalApps: 0,
            totalMenus: 0,
            phase: "launcher",
            error: null,
            timeTaken: 0,
            xmlId: "", // falsy = all apps, set = restrict to that app
            onlineStats: {
                testedApps: [],
                testedMenus: [],
                testedViews: 0,
                testedFormsViews: 0,
                testedNewRecord: 0,
                testedModals: 0,
                testedFilters: 0,
                studioCount: 0,
                errorMenuCount: 0,
            },
            offlineStats: {
                testedApps: [],
                testedMenus: [],
                testedViews: 0,
                testedFormsViews: 0,
                testedNewRecord: 0,
                testedModals: 0,
                errorMenuCount: 0,
            },
            ...persistedState,
        });
        this.clickbot = null;
    }

    start() {
        this.clickbot = new Clickbot(this.env, this.state);
        return this.clickbot.start();
    }

    stop() {
        this.clickbot?.stop();
    }

    open() {
        this.removeOverlay = this.env.services.overlay.add(ClickbotOverlay, { state: this });
        if (this.state.phase !== "launcher") {
            this.start();
        }
    }

    close() {
        this.clickbot?.stop();
        this.removeOverlay?.();
    }
}
