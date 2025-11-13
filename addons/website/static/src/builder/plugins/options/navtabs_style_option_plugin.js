import { BuilderAction } from "@html_builder/core/builder_action";
import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class NavTabsStyleOption extends BaseOptionComponent {
    static template = "website.NavTabsStyleOption";
    static selector = ".s_tabs";
    static applyTo = ".s_tabs_main";
}

export class NavTabsImagesStyleOption extends BaseOptionComponent {
    static template = "website.NavTabsImagesStyleOption";
    static selector = ".s_tabs_images";
    static applyTo = ".s_tabs_main";
}

class NavTabsStyleOptionPlugin extends Plugin {
    static id = "navTabsOptionStyle";
    static shared = ["isNavItem", "getActiveOverlayButtons", "moveNavItem"];
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, NavTabsStyleOption),
            withSequence(SNIPPET_SPECIFIC_END, NavTabsImagesStyleOption),
        ],
        builder_actions: {
            SetStyleAction,
            SetDirectionAction,
        },
        has_overlay_options: { hasOption: (el) => this.isNavItem(el) },
        get_overlay_buttons: withSequence(0, {
            getButtons: this.getActiveOverlayButtons.bind(this),
        }),
        is_unremovable_selector: ".nav-item",
        unsplittable_node_predicates: this.isUnsplittable,
    };

    setup() {
        this.isEditableRTL = this.config.isEditableRTL;
        this.isBackendRTL = localization.direction === "rtl";
    }

    isNavItem(el) {
        return el.matches(".nav-item") && !!el.closest(".s_tabs, .s_tabs_images");
    }

    getActiveOverlayButtons(target) {
        if (!this.isNavItem(target)) {
            this.overlayTarget = null;
            return [];
        }

        this.overlayTarget = target;
        const buttons = [];
        const reverseButtons = this.isEditableRTL !== this.isBackendRTL;
        const parentStyle = window.getComputedStyle(this.overlayTarget.parentElement);
        const isVertical = parentStyle.flexDirection === "column";
        const previousNavItemEl = this.overlayTarget.previousElementSibling;
        const nextNavItemEl = this.overlayTarget.nextElementSibling;

        if (previousNavItemEl) {
            const direction = isVertical ? "up" : reverseButtons ? "right" : "left";
            buttons.push({
                class: `fa fa-fw fa-angle-${direction}`,
                title: isVertical
                    ? _t("Move up")
                    : this.isEditableRTL
                    ? _t("Move right")
                    : _t("Move left"),
                handler: this.moveNavItem.bind(this, "prev"),
            });
        }

        if (nextNavItemEl) {
            const direction = isVertical ? "down" : reverseButtons ? "left" : "right";
            buttons.push({
                class: `fa fa-fw fa-angle-${direction}`,
                title: isVertical
                    ? _t("Move down")
                    : this.isEditableRTL
                    ? _t("Move left")
                    : _t("Move right"),
                handler: this.moveNavItem.bind(this, "next"),
            });
        }

        if (reverseButtons && !isVertical) {
            buttons.reverse();
        }

        return buttons;
    }

    moveNavItem(direction) {
        const tabHash = this.overlayTarget.querySelector(".nav-link").hash;
        const tabPaneEl = this.overlayTarget.closest("section").querySelector(tabHash);

        if (direction === "prev") {
            const previousNavItemEl = this.overlayTarget.previousElementSibling;
            const previousTabPaneEl = tabPaneEl.previousElementSibling;
            previousNavItemEl.before(this.overlayTarget);
            previousTabPaneEl.before(tabPaneEl);
        } else {
            const nextNavItemEl = this.overlayTarget.nextElementSibling;
            const nextTabPaneEl = tabPaneEl.nextElementSibling;
            nextNavItemEl.after(this.overlayTarget);
            nextTabPaneEl.after(tabPaneEl);
        }
    }

    isUnsplittable(node) {
        return (
            node &&
            node.nodeType === Node.ELEMENT_NODE &&
            node.closest(".s_tabs, .s_tabs_images") &&
            node.closest("li")?.classList.contains("nav-item")
        );
    }
}

const getTabsEl = (editingElement) => editingElement.querySelector(".s_tabs_nav");

export class BaseNavtabsStyleOption extends BuilderAction {
    static id = "baseNavtabsStyle";
    static dependencies = ["navTabsOptionStyle"];
    setup() {
        this.tabsTabsClasses = [
            "card-header",
            "px-0",
            "border-0",
            "overflow-x-auto",
            "overflow-y-hidden",
        ];
        this.navTabsClasses = ["card-header-tabs", "mx-0", "px-2", "border-bottom"];
        this.tabsBtnClasses = ["d-flex", "rounded"];
        this.navBtnClasses = ["d-inline-flex", "nav-pills", "p-2"];

        this.overlayTarget = null;
    }

    moveNavItem(direction) {
        this.dependencies.navTabsOptionStyle.moveNavItem(direction);
    }
    getActiveOverlayButtons(target) {
        return this.dependencies.navTabsOptionStyle.getActiveOverlayButtons(target);
    }
    isNavItem(el) {
        return this.dependencies.navTabsOptionStyle.isNavItem(el);
    }
    getNavEl(editingElement) {
        return editingElement.querySelector(".s_tabs_nav .nav");
    }

    applyDirection(editingElement, direction) {
        // s_tabs_images use flex-md classes, while s_tabs use flex-sm classes
        const isTabsImages = editingElement
            .closest(".s_tabs_common")
            .classList.contains("s_tabs_images");

        const isVertical = direction === "vertical";
        const navEl = this.getNavEl(editingElement);

        editingElement.classList.toggle("row", isVertical);
        editingElement.classList.toggle("s_col_no_resize", isVertical);
        editingElement.classList.toggle("s_col_no_bgcolor", isVertical);
        navEl.classList.toggle(isTabsImages ? "flex-md-column" : "flex-sm-column", isVertical);
        editingElement
            .querySelectorAll(".s_tabs_nav > .nav-link")
            .forEach((linkEl) => linkEl.classList.toggle("py-2", isVertical));
        editingElement
            .querySelector(".s_tabs_nav")
            .classList.toggle(isTabsImages ? "col-md-3" : "col-sm-3", isVertical);
        editingElement
            .querySelector(".s_tabs_content")
            .classList.toggle(isTabsImages ? "col-md-9" : "col-sm-9", isVertical);

        // Clean incompatible leftover classes in vertical mode.
        // See "Fill and Justify" and "Alignment" options.
        if (isVertical) {
            navEl.classList.remove(
                "nav-fill",
                "nav-justified",
                "justify-content-center",
                "justify-content-end",
                "ms-auto",
                "mx-auto"
            );
        }
    }
}

class SetStyleAction extends BaseNavtabsStyleOption {
    static id = "setStyle";
    isApplied({ editingElement, value }) {
        const navEl = this.getNavEl(editingElement);
        // 'nav-buttons' also applies 'nav-pills'
        if (navEl.classList.contains("nav-buttons")) {
            return value === "nav-buttons";
        }
        return navEl.classList.contains(value);
    }
    apply({ editingElement, value }) {
        const isTabs = value === "nav-tabs";
        const isBtns = value === "nav-buttons";
        const tabsEl = getTabsEl(editingElement);
        const navEl = this.getNavEl(editingElement);

        if (isTabs || isBtns) {
            this.applyDirection(editingElement, "horizontal");
        }

        if (isTabs) {
            tabsEl.classList.add(...this.tabsTabsClasses);
            navEl.classList.add(...this.navTabsClasses);
        } else if (isBtns) {
            tabsEl.classList.add(...this.tabsBtnClasses);
            navEl.classList.add(...this.navBtnClasses);
        }
        navEl.classList.add(value);

        editingElement.classList.toggle("card", isTabs);
        tabsEl.classList.toggle("mb-3", !isTabs);
        navEl.classList.toggle("overflow-x-auto", !isTabs);
        navEl.classList.toggle("overflow-y-hidden", !isTabs);
        editingElement.querySelector(".s_tabs_content").classList.toggle("p-3", isTabs);
    }
    clean({ editingElement, value }) {
        const isTabs = value === "nav-tabs";
        const isBtns = value === "nav-buttons";
        const tabsEl = getTabsEl(editingElement);
        const navEl = this.getNavEl(editingElement);

        if (isTabs) {
            tabsEl.classList.remove(...this.tabsTabsClasses);
            navEl.classList.remove(...this.navTabsClasses);
        } else if (isBtns) {
            tabsEl.classList.remove(...this.tabsBtnClasses);
            navEl.classList.remove(...this.navBtnClasses);
        }
        navEl.classList.remove(value);
    }
}
class SetDirectionAction extends BaseNavtabsStyleOption {
    static id = "setDirection";
    isApplied({ editingElement, value }) {
        const classList = this.getNavEl(editingElement).classList;
        const containsFlexColumn =
            classList.contains("flex-sm-column") || classList.contains("flex-md-column");
        return value === "vertical" ? containsFlexColumn : !containsFlexColumn;
    }
    apply({ editingElement, value }) {
        this.applyDirection(editingElement, value);
    }
}

registry.category("website-plugins").add(NavTabsStyleOptionPlugin.id, NavTabsStyleOptionPlugin);
