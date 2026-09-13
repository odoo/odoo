// @ts-check
/** @odoo-module native */

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { Pager } from "@web/components/pager/pager";
import { useAction } from "@web/core/action_port";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { SearchModelEvent } from "@web/core/events";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/translation";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { Breadcrumbs } from "@web/search/breadcrumbs/breadcrumbs";
import { useEmbeddedActions } from "@web/search/embedded_actions_bar/embedded_actions";
import { EmbeddedActionsBar } from "@web/search/embedded_actions_bar/embedded_actions_bar";
import { EmbeddedActionsDropdown } from "@web/search/embedded_actions_bar/embedded_actions_dropdown";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useCommand } from "@web/ui/commands/command_hook";

const STICKY_CLASS = "o_mobile_sticky";

/** @returns {{showEmbedded: boolean, embeddedActions: any[], visibleEmbeddedActions: any[], showAllEmbeddedActions: boolean, newActionIsShared: boolean, newActionName: string, currentEmbeddedAction: any}} */
function makeNoEmbeddedInfos() {
    return {
        showEmbedded: false,
        embeddedActions: [],
        visibleEmbeddedActions: [],
        showAllEmbeddedActions: false,
        newActionIsShared: false,
        newActionName: "",
        currentEmbeddedAction: undefined,
    };
}

const log = makeLogger("web.search.control_panel");

export class ControlPanel extends Component {
    static template = "web.ControlPanel";
    static components = {
        Pager,
        SearchBar,
        Dropdown,
        DropdownItem,
        Breadcrumbs,
        EmbeddedActionsBar,
        EmbeddedActionsDropdown,
    };
    static props = {
        display: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };

    /** @type {any} */
    actionService;
    /** @type {any} */
    pagerProps;
    /** @type {any} */
    notificationService;
    /** @type {any[]} */
    breadcrumbs;
    /** @type {any} */
    orm;
    /** @type {import("@web/search/embedded_actions_bar/embedded_actions").EmbeddedActions | null} */
    embeddedActions;
    /** @type {{el: HTMLElement | null}} */
    root;
    /** @type {any} */
    adaptiveMenuRef;
    /** @type {{embeddedInfos: {showEmbedded: boolean, embeddedActions: any[], newActionIsShared: boolean, newActionName: string, visibleEmbeddedActions: any[], currentEmbeddedAction: any}}} */
    state;
    /** @type {(ev: Event) => void} */
    onScrollThrottledBound;
    /** @type {number} */
    scrollingElementHeight;
    /** @type {number} */
    oldScrollTop;
    /** @type {number} */
    lastScrollTop;
    /** @type {number} */
    initialScrollTop;
    /** @type {boolean} */
    isScrolling;

    setup() {
        useLifecycleLog(log);
        this.actionService = useAction();
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
        this.notificationService = useService("notification");
        this.breadcrumbs = useState(this.env.config.breadcrumbs);
        this.orm = useService("orm");

        this.root = useRef("root");
        this.adaptiveMenuRef = useChildRef();

        this.embeddedActions = useEmbeddedActions();
        this.state = useState({
            embeddedInfos: this.embeddedActions
                ? this.embeddedActions.embeddedInfos
                : makeNoEmbeddedInfos(),
        });

        this.onScrollThrottledBound = this.onScrollThrottled.bind(this);
        this.setupViewSwitcherCommands();
        this.setupMobileStickiness();
    }

    setupViewSwitcherCommands() {
        const { viewSwitcherEntries } = this.env.config;
        for (const view of viewSwitcherEntries || []) {
            useCommand(
                _t("Show %s view", view.name),
                () => {
                    this.switchView(view.type);
                },
                {
                    category: "view_switcher",
                    global: true,
                    isAvailable: () => view.type !== this.env.config.viewType,
                },
            );
        }

        if (viewSwitcherEntries?.length > 1) {
            useHotkey(
                "alt+shift+v",
                () => {
                    this.cycleThroughViews();
                },
                {
                    bypassEditableProtection: true,
                    withOverlay: () =>
                        this.root.el.querySelector("nav.o_cp_switch_buttons"),
                },
            );
        }
    }

    /** @returns {boolean} */
    get adaptsToScroll() {
        return (
            this.env.isSmall &&
            !("adaptToScroll" in this.display && !this.display.adaptToScroll)
        );
    }

    setupMobileStickiness() {
        useEffect(
            () => {
                if (!this.adaptsToScroll) {
                    return;
                }
                const scrollingEl = this.getScrollingElement();
                const resizeObserver = new ResizeObserver((entries) => {
                    for (const entry of entries) {
                        const target = /** @type {any} */ (entry.target);
                        if (this.scrollingElementHeight !== target.scrollHeight) {
                            this.oldScrollTop +=
                                target.scrollHeight - this.scrollingElementHeight;
                            this.scrollingElementHeight = target.scrollHeight;
                        }
                    }
                });
                resizeObserver.observe(scrollingEl);
                scrollingEl.addEventListener("scroll", this.onScrollThrottledBound);
                this.root.el.style.top = "0px";
                this.scrollingElementHeight = scrollingEl.scrollHeight;
                this.oldScrollTop = 0;
                this.lastScrollTop = 0;
                this.initialScrollTop = scrollingEl.scrollTop;
                return () => {
                    resizeObserver.disconnect();
                    scrollingEl.removeEventListener(
                        "scroll",
                        this.onScrollThrottledBound,
                    );
                };
            },
            () => [this.env.isSmall, this.display.adaptToScroll, this.root.el],
        );
    }

    /** @returns {HTMLElement} */
    getScrollingElement() {
        return this.root.el.parentElement;
    }

    /** @returns {Record<string, any>} */
    get display() {
        return {
            layoutActions: true,
            ...this.props.display,
        };
    }

    async onClickShowEmbedded() {
        await this.embeddedActions.toggleBar();
    }

    onScrollThrottled() {
        if (this.isScrolling) {
            return;
        }
        this.isScrolling = true;
        browser.requestAnimationFrame(() => (this.isScrolling = false));

        const scrollTop = this.getScrollingElement().scrollTop;
        const delta = Math.round(scrollTop - this.oldScrollTop);

        if (scrollTop > this.initialScrollTop) {
            this.root.el.classList.add(STICKY_CLASS);
            if (delta <= 0) {
                this.lastScrollTop = Math.min(0, this.lastScrollTop - delta);
            } else {
                this.lastScrollTop = Math.max(
                    -this.root.el.offsetHeight,
                    -this.root.el.offsetTop - delta,
                );
            }
            this.root.el.style.top = `${this.lastScrollTop}px`;
        } else {
            this.root.el.classList.remove(STICKY_CLASS);
            this.lastScrollTop = 0;
        }

        this.oldScrollTop = scrollTop;
    }

    /**
     * @param {{ name: string }} view
     * @returns {string}
     */
    viewSwitcherLabel(view) {
        return _t("%s View", view.name);
    }

    /** @param {import("@web/views/view").ViewType} viewType */
    switchView(viewType, /** @type {any} */ newWindow) {
        return this.actionService.switchView(viewType, {}, { newWindow });
    }

    cycleThroughViews() {
        const currentViewType = this.env.config.viewType;
        const viewSwitcherEntries = this.env.config.viewSwitcherEntries;
        const currentIndex = viewSwitcherEntries.findIndex(
            (/** @type {any} */ entry) => entry.type === currentViewType,
        );
        const nextIndex = (currentIndex + 1) % viewSwitcherEntries.length;
        return this.switchView(viewSwitcherEntries[nextIndex].type);
    }

    /** @param {KeyboardEvent} ev */
    onMainButtonsKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "arrowdown") {
            this.env.searchModel.trigger(SearchModelEvent.FOCUS_VIEW);
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    dropdownifyButtons() {
        const adaptiveMenu = this.adaptiveMenuRef.el;
        if (!adaptiveMenu) {
            return;
        }
        const meaningfulElements = this.getBoxedElements(adaptiveMenu.children);
        for (const el of meaningfulElements) {
            el.classList.add("dropdown-item");
            el.classList.remove("btn");
        }
    }

    /**
     * @param {HTMLCollection} elements
     * @returns {HTMLElement[]}
     */
    getBoxedElements(elements) {
        /** @type {HTMLElement[]} */
        const boxed = [];
        for (const el of [...elements]) {
            const elStyles = el.ownerDocument.defaultView.getComputedStyle(el);
            if (elStyles.getPropertyValue("display") === "contents") {
                boxed.push(...this.getBoxedElements(el.children));
            } else if (elStyles.getPropertyValue("display") === "none") {
                continue;
            } else {
                boxed.push(/** @type {HTMLElement} */ (el));
            }
        }
        return boxed;
    }
}
