/** @odoo-module **/
/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {NavBar} from "@web/webclient/navbar/navbar";
import {useAutofocus, useBus, useService} from "@web/core/utils/hooks";
import {useHotkey} from "@web/core/hotkeys/hotkey_hook";
import {scrollTo} from "@web/core/utils/scrolling";
import {debounce} from "@web/core/utils/timing";
import {fuzzyLookup} from "@web/core/utils/search";
import {WebClient} from "@web/webclient/webclient";
import {patch} from "web.utils";
import {escapeRegExp} from "@web/core/utils/strings";

const {Component, useState, onPatched, onWillPatch} = owl;

// Patch WebClient to show AppsMenu instead of default app
patch(WebClient.prototype, "web_responsive.DefaultAppsMenu", {
    setup() {
        this._super();
        useBus(this.env.bus, "APPS_MENU:STATE_CHANGED", ({detail: state}) => {
            document.body.classList.toggle("o_apps_menu_opened", state);
        });
    },
});

/**
 * @extends Dropdown
 */
export class AppsMenu extends Component {
    setup() {
        super.setup();
        this.state = useState({open: false});
        this.menuService = useService("menu");
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            this.setOpenState(false, false);
        });
        this._setupKeyNavigation();
    }
    setOpenState(open_state, from_home_menu_click) {
        this.state.open = open_state;
        // Load home page with proper systray when opening it from website
        if (from_home_menu_click) {
            var currentapp = this.menuService.getCurrentApp();
            if (currentapp && currentapp.name == "Website") {
                if (window.location.pathname != "/web") {
                    const icon = $(
                        document.querySelector(".o_navbar_apps_menu button > i")
                    );
                    icon.removeClass("fa fa-th-large").append(
                        $("<span/>", {class: "fa fa-spin fa-spinner"})
                    );
                }
                window.location.href = "/web#home";
            } else {
                this.env.bus.trigger("APPS_MENU:STATE_CHANGED", open_state);
            }
        } else {
            this.env.bus.trigger("APPS_MENU:STATE_CHANGED", open_state);
        }
    }

    /**
     * Setup navigation among app menus
     */
    _setupKeyNavigation() {
        const repeatable = {
            allowRepeat: true,
        };
        useHotkey(
            "ArrowRight",
            () => {
                this._onWindowKeydown("next");
            },
            repeatable
        );
        useHotkey(
            "ArrowLeft",
            () => {
                this._onWindowKeydown("prev");
            },
            repeatable
        );
        useHotkey(
            "ArrowDown",
            () => {
                this._onWindowKeydown("next");
            },
            repeatable
        );
        useHotkey(
            "ArrowUp",
            () => {
                this._onWindowKeydown("prev");
            },
            repeatable
        );
        useHotkey("Escape", () => {
            this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");
        });
    }

    _onWindowKeydown(direction) {
        const focusableInputElements = document.querySelectorAll(`.o_app`);
        if (focusableInputElements.length) {
            const focusable = [...focusableInputElements];
            const index = focusable.indexOf(document.activeElement);
            let nextIndex = 0;
            if (direction == "prev" && index >= 0) {
                if (index > 0) {
                    nextIndex = index - 1;
                } else {
                    nextIndex = focusable.length - 1;
                }
            } else if (direction == "next") {
                if (index + 1 < focusable.length) {
                    nextIndex = index + 1;
                } else {
                    nextIndex = 0;
                }
            }
            focusableInputElements[nextIndex].focus();
        }
    }
}

/**
 * Reduce menu data to a searchable format understandable by fuzzyLookup
 *
 * `menuService.getMenuAsTree()` returns array in a format similar to this (only
 * relevant data is shown):
 *
 * ```js
 * // This is a menu entry:
 * {
 *     actionID: 12,       // Or `false`
 *     name: "Actions",
 *     childrenTree: {0: {...}, 1: {...}}}, // List of inner menu entries
 *                                          // in the same format or `undefined`
 * }
 * ```
 *
 * This format is very hard to process to search matches, and it would
 * slow down the search algorithm, so we reduce it with this method to be
 * able to later implement a simpler search.
 *
 * @param {Object} memo
 * Reference to current result object, passed on recursive calls.
 *
 * @param {Object} menu
 * A menu entry, as described above.
 *
 * @returns {Object}
 * Reduced object, without entries that have no action, and with a
 * format like this:
 *
 * ```js
 * {
 *  "Discuss": {Menu entry Object},
 *  "Settings": {Menu entry Object},
 *  "Settings/Technical/Actions/Actions": {Menu entry Object},
 *  ...
 * }
 * ```
 */
function findNames(memo, menu) {
    if (menu.actionID) {
        var result = "";
        if (menu.webIconData) {
            const prefix = menu.webIconData.startsWith("P")
                ? "data:image/svg+xml;base64,"
                : "data:image/png;base64,";
            result = menu.webIconData.startsWith("data:image")
                ? menu.webIconData
                : prefix + menu.webIconData.replace(/\s/g, "");
        }
        menu.webIconData = result;
        memo[menu.name.trim()] = menu;
    }
    if (menu.childrenTree) {
        const innerMemo = _.reduce(menu.childrenTree, findNames, {});
        for (const innerKey in innerMemo) {
            memo[menu.name.trim() + " / " + innerKey] = innerMemo[innerKey];
        }
    }
    return memo;
}

/**
 * @extends Component
 */
export class AppsMenuSearchBar extends Component {
    setup() {
        super.setup();
        this.state = useState({
            results: [],
            offset: 0,
            hasResults: false,
        });
        this.searchBarInput = useAutofocus({refName: "SearchBarInput"});
        this._searchMenus = debounce(this._searchMenus, 100);
        // Store menu data in a format searchable by fuzzy.js
        this._searchableMenus = [];
        this.menuService = useService("menu");
        for (const menu of this.menuService.getApps()) {
            Object.assign(
                this._searchableMenus,
                _.reduce([this.menuService.getMenuAsTree(menu.id)], findNames, {})
            );
        }
        // Set up key navigation
        this._setupKeyNavigation();
        onWillPatch(() => {
            // Allow looping on results
            if (this.state.offset < 0) {
                this.state.offset = this.state.results.length + this.state.offset;
            } else if (this.state.offset >= this.state.results.length) {
                this.state.offset -= this.state.results.length;
            }
        });
        onPatched(() => {
            // Scroll to selected element on keyboard navigation
            if (this.state.results.length) {
                const listElement = document.querySelector(".search-results");
                const activeElement = listElement.querySelector(".highlight");
                if (activeElement) {
                    scrollTo(activeElement, listElement);
                }
            }
        });
    }

    /**
     * Search among available menu items, and render that search.
     */
    _searchMenus() {
        const query = this.searchBarInput.el.value;
        this.state.hasResults = query !== "";
        this.state.results = this.state.hasResults
            ? fuzzyLookup(query, _.keys(this._searchableMenus), (k) => k)
            : [];
    }

    /**
     * Get menu object for a given key.
     * @param {String} key Full path to requested menu.
     * @returns {Object} Menu object.
     */
    _menuInfo(key) {
        return this._searchableMenus[key];
    }

    /**
     * Setup navigation among search results
     */
    _setupKeyNavigation() {
        useHotkey("Home", () => {
            this.state.offset = 0;
        });
        useHotkey("End", () => {
            this.state.offset = this.state.results.length - 1;
        });
    }

    _onKeyDown(ev) {
        if (ev.code === "Escape") {
            ev.stopPropagation();
            ev.preventDefault();
            const query = this.searchBarInput.el.value;
            if (query) {
                this.searchBarInput.el.value = "";
                this.state.results = [];
                this.state.hasResults = false;
            } else {
                this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");
            }
        } else if (ev.code === "Tab") {
            if (document.querySelector(".search-results")) {
                ev.preventDefault();
                if (ev.shiftKey) {
                    this.state.offset--;
                } else {
                    this.state.offset++;
                }
            }
        } else if (ev.code === "ArrowUp") {
            if (document.querySelector(".search-results")) {
                ev.preventDefault();
                this.state.offset--;
            }
        } else if (ev.code === "ArrowDown") {
            if (document.querySelector(".search-results")) {
                ev.preventDefault();
                this.state.offset++;
            }
        } else if (ev.code === "Enter") {
            if (this.state.results.length) {
                ev.preventDefault();
                document.querySelector(".search-results .highlight").click();
            }
        }
    }

    _splitName(name) {
        const searchValue = this.searchBarInput.el.value;
        if (name) {
            const splitName = name.split(
                new RegExp(`(${escapeRegExp(searchValue)})`, "ig")
            );
            return searchValue.length && splitName.length > 1 ? splitName : [name];
        }
        return [];
    }
}

// Patch Navbar to add proper icon for apps
patch(NavBar.prototype, "web_responsive.navbar", {
    getWebIconData(menu) {
        var result = "/web_responsive/static/img/default_icon_app.png";
        if (menu.webIconData) {
            const prefix = menu.webIconData.startsWith("P")
                ? "data:image/svg+xml;base64,"
                : "data:image/png;base64,";
            result = menu.webIconData.startsWith("data:image")
                ? menu.webIconData
                : prefix + menu.webIconData.replace(/\s/g, "");
        }
        return result;
    },
});
AppsMenu.template = "web_responsive.AppsMenu";
AppsMenuSearchBar.template = "web_responsive.AppsMenuSearchResults";
Object.assign(NavBar.components, {AppsMenu, AppsMenuSearchBar});
