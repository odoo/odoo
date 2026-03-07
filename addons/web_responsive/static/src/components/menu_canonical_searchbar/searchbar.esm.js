/* global console */
/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Component, onPatched, onWillPatch, useRef, useState} from "@odoo/owl";
import {
    collectRootMenuItems,
    collectSubMenuItems,
} from "@web_responsive/components/apps_menu_tools.esm";
import {useAutofocus, useService} from "@web/core/utils/hooks";
import {debounce} from "@web/core/utils/timing";
import {escapeRegExp} from "@web/core/utils/strings";
import {fuzzyLookup} from "@web/core/utils/search";
import {scrollTo} from "@web/core/utils/scrolling";

/**
 * @extends Component
 */
export class AppsMenuCanonicalSearchBar extends Component {
    setup() {
        super.setup();
        this.state = useState({
            rootItems: [],
            subItems: [],
            offset: 0,
            hasResults: false,
        });
        this.searchBarInput = useAutofocus({refName: "SearchBarInput"});
        this._searchMenus = debounce(this._searchMenus, 200);
        this.menuService = useService("menu");
        this.searchItemsRef = useRef("searchItems");
        this.rootMenuItems = this.getRootMenuItems();
        this.subMenuItems = this.getSubMenuItems();
        onWillPatch(this._computeResultOffset);
        onPatched(this._scrollToHighlight);
    }

    /**
     * @returns {String}
     */
    get inputValue() {
        const {el} = this.searchBarInput;
        return el ? el.value : "";
    }

    /**
     * @returns {Boolean}
     */
    get hasItemsToDisplay() {
        return this.totalItemsCount > 0;
    }

    /**
     * @returns {Number}
     */
    get totalItemsCount() {
        const {rootItems, subItems} = this.state;
        return rootItems.length + subItems.length;
    }

    /**
     * @param {Number} index
     * @param {Boolean} isSubMenu
     * @returns {String}
     */
    highlighted(index, isSubMenu = false) {
        const {state} = this;
        let _index = index;
        if (isSubMenu) {
            _index = state.rootItems.length + index;
        }
        return _index === state.offset ? "highlight" : "";
    }

    /**
     * @returns {Object[]}
     */
    getRootMenuItems() {
        return this.menuService.getApps().reduce(collectRootMenuItems, []);
    }

    /**
     * @returns {Object[]}
     */
    getSubMenuItems() {
        const response = [];
        for (const menu of this.menuService.getApps()) {
            const menuTree = this.menuService.getMenuAsTree(menu.id);
            collectSubMenuItems(response, null, menuTree);
        }
        return response;
    }

    /**
     * Search among available menu items, and render that search.
     */
    _searchMenus() {
        const {state} = this;
        const query = this.inputValue;
        state.hasResults = query !== "";
        if (!state.hasResults) {
            state.rootItems = [];
            state.subItems = [];
            return;
        }
        const searchField = (item) => item.displayName;
        // Update search results paths
        for (const root in this.rootMenuItems) {
            // Root is an app
            if (this.rootMenuItems[root]?.actionPath) {
                this.rootMenuItems[root].path =
                    `/odoo/${this.rootMenuItems[root].actionPath}`;
            }
            // Root is a module
            else {
                this.rootMenuItems[root].path =
                    `/odoo/action-${this.rootMenuItems[root].actionID}`;
            }
        }
        for (const item in this.subMenuItems) {
            for (const root in this.rootMenuItems) {
                if (this.subMenuItems[item].appID === this.rootMenuItems[root].appID) {
                    // Root is an app
                    if (this.rootMenuItems[root]?.actionPath) {
                        this.subMenuItems[item].path =
                            `/odoo/${this.rootMenuItems[root].actionPath}/action-${this.subMenuItems[item].actionID}`;
                    }
                    // Root is a module
                    else {
                        this.subMenuItems[item].path =
                            `/odoo/action-${this.subMenuItems[item].actionID}`;
                    }
                }
            }
        }
        state.rootItems = fuzzyLookup(query, this.rootMenuItems, searchField);
        state.subItems = fuzzyLookup(query, this.subMenuItems, searchField);
    }

    _onKeyDown(ev) {
        const code = ev.code;
        if (code === "Escape") {
            ev.stopPropagation();
            ev.preventDefault();
            if (this.inputValue) {
                this.searchBarInput.el.value = "";
                Object.assign(this.state, {rootItems: [], subItems: []});
                this.state.hasResults = false;
            } else {
                this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");
            }
        } else if (code === "Tab") {
            if (this.searchItemsRef.el) {
                ev.preventDefault();
                if (ev.shiftKey) {
                    this.state.offset--;
                } else {
                    this.state.offset++;
                }
            }
        } else if (code === "ArrowUp") {
            if (this.searchItemsRef.el) {
                ev.preventDefault();
                this.state.offset--;
            }
        } else if (code === "ArrowDown") {
            if (this.searchItemsRef.el) {
                ev.preventDefault();
                this.state.offset++;
            }
        } else if (code === "Enter") {
            const element = this.searchItemsRef.el;
            if (this.hasItemsToDisplay && element) {
                ev.preventDefault();
                this._selectHighlightedSearchItem(element);
            }
        } else if (code === "Home") {
            this.state.offset = 0;
        } else if (code === "End") {
            this.state.offset = this.totalItemsCount - 1;
        }
    }

    /**
     * @param {HTMLElement} element
     * @private
     */
    _selectHighlightedSearchItem(element) {
        const highlightedElement = element.querySelector(
            ".highlight > .search-item__link"
        );
        if (highlightedElement) {
            highlightedElement.click();
        } else {
            console.warn("Highlighted search item is not found");
        }
    }

    _splitName(name) {
        if (!name) {
            return [];
        }
        const value = this.inputValue;
        const splitName = name.split(new RegExp(`(${escapeRegExp(value)})`, "ig"));
        return value.length && splitName.length > 1 ? splitName : [name];
    }

    _scrollToHighlight() {
        // Scroll to selected element on keyboard navigation
        const element = this.searchItemsRef.el;
        if (!(this.totalItemsCount && element)) {
            return;
        }
        const activeElement = element.querySelector(".highlight");
        if (activeElement) {
            scrollTo(activeElement, element);
        }
    }

    _computeResultOffset() {
        // Allow looping on results
        const {state} = this;
        const total = this.totalItemsCount;
        if (state.offset < 0) {
            state.offset = total + state.offset;
        } else if (state.offset >= total) {
            state.offset -= total;
        }
    }
}

AppsMenuCanonicalSearchBar.props = {};
AppsMenuCanonicalSearchBar.template = "web_responsive.AppsMenuCanonicalSearchBar";
