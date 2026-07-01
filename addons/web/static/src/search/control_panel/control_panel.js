import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Pager } from "@web/core/pager/pager";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useCommand } from "@web/core/commands/command_hook";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { Breadcrumbs } from "../breadcrumbs/breadcrumbs";

import { Component, onMounted, plugin, props, proxy, t } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { EmbeddedActionsPanel, useEmbeddedActions } from "./embedded_actions";

const STICKY_CLASS = "o_mobile_sticky";
const DEFAULT_DISPLAY = {
    actions: true,
    buttons: true,
};

export class ControlPanel extends Component {
    static template = "web.ControlPanel";
    static components = {
        Pager,
        Dropdown,
        DropdownItem,
        Breadcrumbs,
        EmbeddedActionsPanel,
    };
    props = props({
        display: t.object().optional(DEFAULT_DISPLAY),
        slots: t.object().optional(),
    });

    setup() {
        this.embeddedPanelState = useEmbeddedActions();
        this.actionService = useService("action");
        this.offlinePlugin = plugin(OfflinePlugin);
        this.pagerProps = this.env.config.pagerProps
            ? proxy(this.env.config.pagerProps)
            : undefined;
        this.breadcrumbs = proxy(this.env.config.breadcrumbs);

        this.root = useRef("root");
        this.onScrollThrottledBound = this.onScrollThrottled.bind(this);

        const { viewSwitcherEntries, viewType } = this.env.config;
        for (const view of viewSwitcherEntries || []) {
            useCommand(_t("Show %s view", view.name), () => this.switchView(view.type), {
                category: "view_switcher",
                isAvailable: () => view.type !== viewType,
            });
        }

        if (viewSwitcherEntries?.length > 1) {
            useHotkey(
                "alt+shift+v",
                () => {
                    this.cycleThroughViews();
                },
                {
                    bypassEditableProtection: true,
                    withOverlay: () => this.root.el.querySelector("nav.o_cp_switch_buttons"),
                }
            );
        }

        useLayoutEffect(() => {
            if (
                !this.env.isSmall ||
                ("adaptToScroll" in this.display && !this.display.adaptToScroll)
            ) {
                return;
            }
            const scrollingEl = this.getScrollingElement();
            this.scrollingElementResizeObserver.observe(scrollingEl);
            scrollingEl.addEventListener("scroll", this.onScrollThrottledBound);
            this.root.el.style.top = "0px";
            this.scrollingElementHeight = scrollingEl.scrollHeight;
            return () => {
                this.scrollingElementResizeObserver.unobserve(scrollingEl);
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
    }

    scrollingElementResizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
            if (this.scrollingElementHeight !== entry.target.scrollingElementHeight) {
                this.oldScrollTop +=
                    entry.target.scrollingElementHeight - this.scrollingElementHeight;
                this.scrollingElementHeight = entry.target.scrollingElementHeight;
            }
        }
    });

    getScrollingElement() {
        return this.root.el.parentElement;
    }

    get display() {
        return {
            ...DEFAULT_DISPLAY,
            ...this.props.display,
        };
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
                    -this.root.el.offsetTop - delta
                );
            }
            this.root.el.style.top = `${this.lastScrollTop}px`;
        } else {
            this.root.el.classList.remove(STICKY_CLASS);
            this.lastScrollTop = 0;
        }
        this.oldScrollTop = scrollTop;
    }

    isViewAvailable(view) {
        return (
            !this.offlinePlugin.isOffline() ||
            this.offlinePlugin.isAvailableOffline(this.env.config.actionId, view.type)
        );
    }

    switchView(viewType, newWindow) {
        this.actionService.switchView(viewType, {}, { newWindow });
    }

    cycleThroughViews() {
        const currentViewType = this.env.config.viewType;
        const viewSwitcherEntries = this.env.config.viewSwitcherEntries;
        const currentIndex = viewSwitcherEntries.findIndex(
            (entry) => entry.type === currentViewType
        );
        const nextIndex = (currentIndex + 1) % viewSwitcherEntries.length;
        this.switchView(viewSwitcherEntries[nextIndex].type);
    }

    onMainButtonsKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "arrowdown") {
            this.env.searchModel.trigger("focus-view");
            ev.preventDefault();
            ev.stopPropagation();
        }
    }

    dropdownifyButtons() {
        const adaptiveMenu = document.querySelector(
            ".o-control-panel-adaptive-dropdown.dropdown-menu"
        );
        const meaningfulElements = this.getBoxedElements(adaptiveMenu.children);
        for (const el of meaningfulElements) {
            el.classList.add("dropdown-item");
            el.classList.remove("btn");
        }
    }

    getBoxedElements(elements) {
        const boxed = [];
        for (const el of [...elements]) {
            const elStyles = el.ownerDocument.defaultView.getComputedStyle(el);
            if (elStyles.getPropertyValue("display") === "contents") {
                boxed.push(...this.getBoxedElements(el.children));
            } else if (elStyles.getPropertyValue("display") === "none") {
                continue;
            } else {
                boxed.push(el);
            }
        }
        return boxed;
    }
}
