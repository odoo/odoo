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
    "website_sale.menu_open_shop", // menu that opens a website editor
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
};

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
                testedFormsViews: 0,
                appIndex: 0,
                menuIndex: 0,
                errorMenuCount: 0,
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
            if (this.state.errorMenuCount === 0) {
                console.log(SUCCESS_SIGNAL);
            } else {
                console.error(FAILURE_SIGNAL);
            }
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
        console.log(`Tested ${this.state.testedApps.length} apps`);
        console.log(`Tested ${this.state.testedMenus.length} menus`);
        if (this.state.errorMenuCount > 0) {
            console.log(`Error found while testing ${this.state.errorMenuCount} menus`);
        }
        console.log(`Tested ${this.state.testedViews} views`);
        console.log(`Tested ${this.state.testedFormsViews} form views`);
        console.log(`Tested ${this.state.testedModals} modals`);
        console.log(`Tested ${this.state.testedFilters} filters`);
        if (this.state.studioCount > 0) {
            console.log(`Tested ${this.state.studioCount} views in Studio`);
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
            throw new Error(
                `No element "${elDescription}" found. Testing "${this.currentMenu.name}" ("${this.currentMenu.xmlid}") menu.`
            );
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
                    `Error dialog detected ${
                        document.querySelector(".o_error_dialog").innerHTML
                    }\n on testing menu ${this.currentMenu.name} (${this.currentMenu.xmlid})`
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
                    await this._testClickingRecord();
                }
            } else {
                await this._triggerClick(filter, `filter "${filter.innerText.trim()}"`);
                await this._waitForCondition(() => true);
                await this._testClickingRecord();
            }
        }
    }

    /**
     * Test clicking on a record in list or kanban view
     * @returns {Promise}
     */

    async _testClickingRecord() {
        if (BLACKLISTED_RECORD_ACTIONS.has(this.currentMenu.xmlid)) {
            console.log(
                `Skipping blacklisted form menu ${this.currentMenu.name} (${this.currentMenu.xmlid})`
            );
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
                // Open the first record in the list
                if (document.querySelector(".o_list_record_open_form_view")) {
                    await this._triggerClick(
                        row.querySelector(".o_list_record_open_form_view"),
                        "open form view from list (View Button)"
                    );
                } else {
                    await this._triggerClick(
                        row.querySelector(".o_data_cell"),
                        "open form view from list"
                    );
                }
                if (exceptionActions?.list?.toCheck) {
                    await this._waitForCondition(
                        () => document.querySelector(exceptionActions?.list?.toCheck) !== null
                    );
                } else {
                    // Wait for the form view to be loaded or the list to be editable
                    await this._waitForCondition(
                        () =>
                            document.querySelector(".o_form_view") !== null ||
                            document.querySelector(".o_data_row.o_selected_row") !== null
                    );
                }

                // Go back to the list
                if (exceptionActions?.list?.toGoBack) {
                    await this._triggerClick(
                        document.querySelector(exceptionActions?.list?.toGoBack),
                        "go back to list view"
                    );
                } else if (document.querySelector(".o_form_view")) {
                    this.formviewTested = true;
                    this.state.testedFormsViews++;
                    await this._triggerClick(
                        document.querySelector(".o_back_button"),
                        "go back to list view"
                    );
                } else {
                    await this._triggerClick(
                        document.querySelector(".o_list_button_discard"),
                        "discard the editable list"
                    );
                }
                await this._waitForCondition(() => document.querySelector(`.o_list_view`) !== null);
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
                // Open the first record in the kanban
                await this._triggerClick(card, "open form view from kanban");
                if (exceptionActions?.kanban?.toCheck) {
                    await this._waitForCondition(
                        () => document.querySelector(exceptionActions?.kanban?.toCheck) !== null
                    );
                } else {
                    await this._waitForCondition(
                        () => document.querySelector(`.o_form_view`) !== null
                    );
                }

                // Go back to the kanban
                if (exceptionActions?.kanban?.toGoBack) {
                    await this._triggerClick(
                        document.querySelector(exceptionActions?.kanban?.toGoBack),
                        "go back to kanban view"
                    );
                } else {
                    // form view
                    this.formviewTested = true;
                    this.state.testedFormsViews++;
                    await this._triggerClick(
                        document.querySelector(".o_back_button"),
                        "go back to kanban view"
                    );
                }
                await this._waitForCondition(
                    () => document.querySelector(`.o_kanban_view`) !== null
                );
            }
        }
    }

    async _testView() {
        this.recordTested = false;
        await this._testClickingRecord();
        await this._testStudio();
        await this._testFilters();
    }

    async _testViews() {
        this.formviewTested = false;
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
            if (err instanceof ClickbotStopError) {
                throw err;
            }
            this.state.errorMenuCount++;
            console.error(err.message);
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
