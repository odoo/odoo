/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Pager } from "@web/core/pager/pager";
import { useService } from "@web/core/utils/hooks";
import { SearchBar } from "../search_bar/search_bar";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useCommand } from "@web/core/commands/command_hook";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component, useState, onMounted, useExternalListener, useRef, useEffect } from "@odoo/owl";

const STICKY_CLASS = "o_mobile_sticky";

export class ControlPanel extends Component {
    setup() {
        this.actionService = useService("action");
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
        this.breadcrumbs = useState(this.env.config.breadcrumbs);

        this.root = useRef("root");

        this.state = useState({
            showSearchBar: false,
            showMobileSearch: false,
            showViewSwitcher: false,
        });

        this.onScrollThrottledBound = this.onScrollThrottled.bind(this);

        const { viewSwitcherEntries, viewType } = this.env.config;
        for (const view of viewSwitcherEntries || []) {
            useCommand(_t("Show %s view", view.name), () => this.onViewClicked(view.type), {
                category: "view_switcher",
                isAvailable: () => view.type !== viewType,
            });
        }

        useExternalListener(window, "click", this.onWindowClick);
        useEffect(() => {
            if (
                !this.env.isSmall ||
                ("adaptToScroll" in this.display && !this.display.adaptToScroll)
            ) {
                return;
            }
            const scrollingEl = this.getScrollingElement();
            scrollingEl.addEventListener("scroll", this.onScrollThrottledBound);
            this.root.el.style.top = "0px";
            return () => {
                scrollingEl.removeEventListener("scroll", this.onScrollThrottledBound);
            };
        });
        onMounted(() => {
            if (
                !this.env.isSmall ||
                ("adaptToScroll" in this.display && !this.display.adaptToScroll)
            ) {
                return;
            }
            this.oldScrollTop = 0;
            this.lastScrollTop = 0;
            this.initialScrollTop = this.getScrollingElement().scrollTop;
        });

        this.mainButtons = useRef("mainButtons");

        useEffect(() => {
            // on small screen, clean-up the dropdown elements
            const dropdownButtons = this.mainButtons.el.querySelectorAll(
                ".o_control_panel_collapsed_create.dropdown-menu button"
            );
            if (!dropdownButtons.length) {
                this.mainButtons.el
                    .querySelectorAll(
                        ".o_control_panel_collapsed_create.dropdown-menu, .o_control_panel_collapsed_create.dropdown-toggle"
                    )
                    .forEach((el) => el.classList.add("d-none"));
                this.mainButtons.el
                    .querySelectorAll(".o_control_panel_collapsed_create.btn-group")
                    .forEach((el) => el.classList.remove("btn-group"));
                return;
            }
            for (const button of dropdownButtons) {
                for (const cl of Array.from(button.classList)) {
                    button.classList.toggle(cl, !cl.startsWith("btn-"));
                }
                button.classList.add("dropdown-item", "btn", "btn-link");
            }
        });
    }

    getScrollingElement() {
        return this.root.el.parentElement;
    }

    /**
     * Reset mobile search state
     */
    resetSearchState() {
        Object.assign(this.state, {
            showSearchBar: false,
            showMobileSearch: false,
            showViewSwitcher: false,
        });
    }

    /**
     * @returns {Object}
     */
    get display() {
        return {
            layoutActions: true,
            ...this.props.display,
        };
    }

    /**
     * Called when an element of the breadcrumbs is clicked.
     *
     * @param {string} jsId
     */
    onBreadcrumbClicked(jsId) {
        this.actionService.restore(jsId);
    }

    /**
     * Show or hide the control panel on the top screen.
     * The function is throttled to avoid refreshing the scroll position more
     * often than necessary.
     */
    onScrollThrottled() {
        if (this.isScrolling) {
            return;
        }
        this.isScrolling = true;
        browser.requestAnimationFrame(() => (this.isScrolling = false));

        const scrollTop = this.getScrollingElement().scrollTop;
        const delta = Math.round(scrollTop - this.oldScrollTop);

        if (scrollTop > this.initialScrollTop) {
            // Beneath initial position => sticky display
            this.root.el.classList.add(STICKY_CLASS);
            if (delta < 0) {
                // Going up
                this.lastScrollTop = Math.min(0, this.lastScrollTop - delta);
            } else {
                // Going down | not moving
                this.lastScrollTop = Math.max(
                    -this.root.el.offsetHeight,
                    -this.root.el.offsetTop - delta
                );
            }
            this.root.el.style.top = `${this.lastScrollTop}px`;
        } else {
            // Above initial position => standard display
            this.root.el.classList.remove(STICKY_CLASS);
            this.lastScrollTop = 0;
        }

        this.oldScrollTop = scrollTop;
    }

    /**
     * Called when a view is clicked in the view switcher
     * and reset mobile search state on switch view.
     *
     * @param {ViewType} viewType
     */
    onViewClicked(viewType) {
        this.resetSearchState();
        this.actionService.switchView(viewType);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    onWindowClick(ev) {
        if (this.state.showViewSwitcher && !ev.target.closest(".o_cp_switch_buttons")) {
            this.state.showViewSwitcher = false;
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onMainButtonsKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "arrowdown") {
            this.env.searchModel.trigger("focus-view");
            ev.preventDefault();
            ev.stopPropagation();
        }
    }
}

ControlPanel.components = {
    Pager,
    SearchBar,
    Dropdown,
    DropdownItem,
};
ControlPanel.template = "web.ControlPanel";
ControlPanel.props = {
    display: { type: Object, optional: true },
    slots: { type: Object, optional: true },
};
