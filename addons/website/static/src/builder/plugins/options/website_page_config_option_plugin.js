import { after } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rgbaToHex } from "@web/core/utils/colors";
import { withSequence } from "@html_editor/utils/resource";
import { FOOTER_COPYRIGHT } from "./footer_option_plugin";
import { HEADER_TEMPLATE } from "./header/header_option_plugin";
import { TopMenuVisibilityOption } from "./website_page_config_option";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BreadcrumbOption } from "./breadcrumb_option";

/**
 * @typedef { Object } WebsitePageConfigOptionShared
 * @property { WebsitePageConfigOptionPlugin['setDirty'] } setDirty
 * @property { WebsitePageConfigOptionPlugin['setFooterVisible'] } setFooterVisible
 * @property { WebsitePageConfigOptionPlugin['getVisibilityItem'] } getVisibilityItem
 * @property { WebsitePageConfigOptionPlugin['getFooterVisibility'] } getFooterVisibility
 * @property { WebsitePageConfigOptionPlugin['doesPageOptionExist'] } doesPageOptionExist
 */

export const TOP_MENU_VISIBILITY = after(HEADER_TEMPLATE);
export const HIDE_FOOTER = after(FOOTER_COPYRIGHT);

export class HideFooterOption extends BaseOptionComponent {
    static template = "website.HideFooterOption";
    static selector =
        "[data-main-object]:has(input.o_page_option_data[name='footer_visible']) #wrapwrap > footer";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class WebsitePageConfigOptionPlugin extends Plugin {
    static id = "websitePageConfigOptionPlugin";
    static dependencies = ["history", "visibility", "builderActions"];
    static shared = [
        "setDirty",
        "setFooterVisible",
        "getVisibilityItem",
        "getFooterVisibility",
        "doesPageOptionExist",
        "getTarget",
    ];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetWebsiteHeaderVisibilityAction,
            SetWebsiteFooterVisibleAction,
            SetPageWebsiteDirtyAction,
            SetWebsiteBreadcrumbVisibilityAction,
        },
        builder_options: [
            withSequence(TOP_MENU_VISIBILITY, TopMenuVisibilityOption),
            withSequence(HIDE_FOOTER, HideFooterOption),
            BreadcrumbOption,
        ],
        target_show: this.onTargetVisibilityToggle.bind(this, true),
        target_hide: this.onTargetVisibilityToggle.bind(this, false),
        save_handlers: this.onSave.bind(this),
    };

    /**
     * Returns the HTML element corresponding to the given type.
     *
     * @param {'header' | 'breadcrumb'} type The element type to retrieve.
     * @returns {HTMLElement | null} The matching element or null if not found.
     */
    getTarget(type) {
        if (type === "header") {
            return this.document.querySelector("#wrapwrap > header");
        } else if (type === "breadcrumb") {
            return this.document.querySelector("#wrapwrap div.o_page_breadcrumb");
        }
        return null;
    }

    /**
     * Get the current visibility state of the target element.
     *
     * @param {'header' | 'breadcrumb'} type The target element type.
     * @returns {'regular' | 'overTheContent' | 'hidden'} The visibility state.
     */
    getVisibilityItem(type) {
        const el = this.getTarget(type);
        if (!el) {
            return "regular";
        }
        const isHidden = el.classList.contains("o_snippet_invisible");
        let isOverlay = null;
        if (type === "header") {
            isOverlay = this.document
                .getElementById("wrapwrap")
                .classList.contains("o_header_overlay");
        } else if (type === "breadcrumb") {
            isOverlay = this.document
                .querySelector("main")
                .classList.contains("o_breadcrumb_overlay");
        }
        return isOverlay ? "overTheContent" : isHidden ? "hidden" : "regular";
    }

    getFooterVisibility() {
        return this.document
            .querySelector("#wrapwrap > footer")
            .classList.contains("o_snippet_invisible");
    }

    /**
     * Get the color value (class or inline style) of the target element.
     *
     * @param {'header' | 'breadcrumb'} type The target element type.
     * @param {String} attribute CSS property to check.
     * @param {String} classPrefix Class prefix to match (e.g. "bg-" | "text-")
     * @returns {String | null} Matching class name | hex color | null.
     */
    getColorValue(type, attribute, classPrefix) {
        const el = this.getTarget(type);
        if (!el) {
            return null;
        }
        const matchingClass = [...el.classList].find((cls) => cls.startsWith(classPrefix));
        return matchingClass || rgbaToHex(el.style.getPropertyValue(attribute));
    }

    setDirty(isPreviewing) {
        if (isPreviewing) {
            return;
        }
        this.isDirty = true;
    }

    onSave() {
        if (!this.isDirty) {
            return;
        }
        const headerItem = this.getVisibilityItem("header");
        const breadcrumbItem = this.getVisibilityItem("breadcrumb");

        const pageOptions = {
            header_overlay: () => headerItem === "overTheContent",
            header_color: () => this.getColorValue("header", "background-color", "bg-"),
            header_text_color: () => this.getColorValue("header", "color", "text-"),
            header_visible: () => headerItem !== "hidden",
            footer_visible: () => !this.getFooterVisibility(),

            breadcrumb_overlay: () => breadcrumbItem === "overTheContent",
            breadcrumb_color: () => this.getColorValue("breadcrumb", "background-color", "bg-"),
            breadcrumb_text_color: () => this.getColorValue("breadcrumb", "color", "text-"),
            breadcrumb_visible: () => breadcrumbItem !== "hidden",
        };

        const args = {};
        for (const [pageOptionName, valueGetter] of Object.entries(pageOptions)) {
            if (this.doesPageOptionExist(pageOptionName)) {
                args[pageOptionName] = valueGetter();
            }
        }

        const mainObject = this.services.website.currentWebsite.metadata.mainObject;
        return Promise.all([this.services.orm.write(mainObject.model, [mainObject.id], args)]);
    }

    doesPageOptionExist(pageOptionName) {
        return this.document.querySelector(
            `[data-main-object]:has(input.o_page_option_data[name='${pageOptionName}'])`
        );
    }

    setFooterVisible(show) {
        const footerEl = this.document.querySelector("#wrapwrap > footer");
        footerEl.classList.toggle("d-none", !show);
        footerEl.classList.toggle("o_snippet_invisible", !show);
        this.dependencies.visibility.onOptionVisibilityUpdate(footerEl, show);
    }

    onTargetVisibilityToggle(show, target) {
        if (show && target.matches("#wrapwrap > header")) {
            this.dependencies.builderActions.applyAction("setWebsiteHeaderVisibility", {
                editingElement: target,
                value: "regular",
                isPreviewing: false,
            });
        }
        if (show && target.matches(".o_page_breadcrumb")) {
            this.dependencies.builderActions.applyAction("setWebsiteBreadcrumbVisibility", {
                editingElement: target,
                value: "regular",
                isPreviewing: false,
            });
        }
        if (show && target.matches("#wrapwrap > footer")) {
            this.dependencies.builderActions.applyAction("setWebsiteFooterVisible", {
                editingElement: target,
                isPreviewing: false,
            });
        }
    }
}
export class BaseWebsitePageConfigAction extends BuilderAction {
    static id = "baseWebsitePageConfig";
    static dependencies = ["websitePageConfigOptionPlugin", "history", "visibility"];
    setup() {
        this.websitePageConfig = this.dependencies.websitePageConfigOptionPlugin;
        this.visibility = this.dependencies.visibility;
        this.history = this.dependencies.history;
        this.headerVisibilityHandlers = this.getVisibilityHandlers("header");
        this.breadcrumbVisibilityHandlers = this.getVisibilityHandlers("breadcrumb");
    }

    getVisibilityHandlers(type) {
        return {
            overTheContent: () => {
                this.setOverlay(type, true);
                this.setVisible(type, false);
            },
            regular: () => {
                this.setOverlay(type, false);
                this.setVisible(type, false);
                this.resetColor(type);
                this.resetTextColor(type);
            },
            hidden: () => {
                this.setOverlay(type, false);
                this.setVisible(type, true);
                this.resetColor(type);
                this.resetTextColor(type);
            },
        };
    }

    /**
     * Apply or remove "Over the Content" mode for the target element.
     *
     * @param {'header' | 'breadcrumb'} type The element type to update.
     * @param {boolean} shouldApply true to enable, false to disable.
     */
    setOverlay(type, shouldApply) {
        const selector = type === "header" ? "#wrapwrap" : type === "breadcrumb" ? "main" : null;
        const el = this.document.querySelector(selector);
        el.classList.toggle(`o_${type}_overlay`, shouldApply);
    }

    /**
     * Toggle the visibility of a target element and update the plugin's
     * visibility state.
     *
     * @param {'header' | 'breadcrumb'} type The element type to toggle.
     * @param {boolean} shouldHide true to hide, false to show.
     */
    setVisible(type, shouldHide) {
        const el = this.websitePageConfig.getTarget(type);
        el.classList.toggle("d-none", shouldHide);
        el.classList.toggle("o_snippet_invisible", shouldHide);
        this.visibility.onOptionVisibilityUpdate(el, !shouldHide);
    }

    /**
     * Remove any background color class or inline style from the given
     * target element.
     *
     * @param {'header' | 'breadcrumb'} type The element type to reset.
     */
    resetColor(type) {
        const el = this.websitePageConfig.getTarget(type);
        el.style.removeProperty("background-color");
        const classes = [...el.classList].filter((cls) => cls.startsWith("bg-o-color-"));
        if (classes.length) {
            el.classList.remove(...classes);
        }
    }

    /**
     * Remove any text color class or inline style from the given
     * target element.
     *
     * @param {'header' | 'breadcrumb'} type The element type to reset.
     */
    resetTextColor(type) {
        const el = this.websitePageConfig.getTarget(type);
        el.style.removeProperty("color");
        const classes = [...el.classList].filter((cls) => cls.startsWith("text-o-color-"));
        if (classes.length) {
            el.classList.remove(...classes);
        }
    }
}
export class SetWebsiteHeaderVisibilityAction extends BaseWebsitePageConfigAction {
    static id = "setWebsiteHeaderVisibility";
    apply({ editingElement, value: headerPositionValue, isPreviewing }) {
        const lastValue = this.websitePageConfig.getVisibilityItem("header");
        this.history.applyCustomMutation({
            apply: () => this.headerVisibilityHandlers[headerPositionValue](),
            revert: () => this.headerVisibilityHandlers[lastValue](),
        });

        this.websitePageConfig.setDirty(isPreviewing);
    }
    isApplied({ editingElement, value }) {
        return this.websitePageConfig.getVisibilityItem("header") === value;
    }
}
export class SetWebsiteBreadcrumbVisibilityAction extends BaseWebsitePageConfigAction {
    static id = "setWebsiteBreadcrumbVisibility";
    isApplied({ value }) {
        return this.websitePageConfig.getVisibilityItem("breadcrumb") === value;
    }
    apply({ value }) {
        const lastValue = this.websitePageConfig.getVisibilityItem("breadcrumb");
        this.history.applyCustomMutation({
            apply: () => this.breadcrumbVisibilityHandlers[value](),
            revert: () => this.breadcrumbVisibilityHandlers[lastValue](),
        });
        this.websitePageConfig.setDirty();
    }
}
export class SetWebsiteFooterVisibleAction extends BaseWebsitePageConfigAction {
    static id = "setWebsiteFooterVisible";
    isApplied({ editingElement }) {
        return !this.websitePageConfig.getFooterVisibility();
    }
    apply({ editingElement, isPreviewing }) {
        this.websitePageConfig.setFooterVisible(true);
        this.websitePageConfig.setDirty(isPreviewing);
    }
    clean({ editingElement, isPreviewing }) {
        this.websitePageConfig.setFooterVisible(false);
        this.websitePageConfig.setDirty(isPreviewing);
    }
}

export class SetPageWebsiteDirtyAction extends BaseWebsitePageConfigAction {
    static id = "setPageWebsiteDirty";
    apply({ editingElement, isPreviewing }) {
        this.websitePageConfig.setDirty(isPreviewing);
    }
}

registry
    .category("website-plugins")
    .add(WebsitePageConfigOptionPlugin.id, WebsitePageConfigOptionPlugin);
