import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba, rgbaToHex } from "@web/core/utils/colors";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getAverageBackgroundImageColor, WHITE_RGB } from "./website_page_config_contrast_utils";

const TARGET_CONFIG = {
    header: {
        selector: "#wrapwrap > header",
        overlaySelector: "#wrapwrap",
        overlayClass: "o_header_overlay",
        action: "setWebsiteHeaderVisibility",
    },
    breadcrumb: {
        selector: "#wrapwrap div.o_page_breadcrumb",
        overlaySelector: "main",
        overlayClass: "o_breadcrumb_overlay",
        action: "setWebsiteBreadcrumbVisibility",
    },
};
const PRESET_NUMBERS = [1, 2, 3, 4, 5];
const COLOR_COMBINATION_REGEX = /^o_cc\d+$/;

function removeMatchingClasses(el, predicate) {
    const classes = [...el.classList].filter(predicate);
    if (classes.length) {
        el.classList.remove(...classes);
    }
}

function isColorCombinationClass(cls) {
    return cls === "o_colored_level" || cls === "o_cc" || COLOR_COMBINATION_REGEX.test(cls);
}

/**
 * @typedef { Object } WebsitePageConfigOptionShared
 * @property { WebsitePageConfigOptionPlugin['setDirty'] } setDirty
 * @property { WebsitePageConfigOptionPlugin['setFooterVisible'] } setFooterVisible
 * @property { WebsitePageConfigOptionPlugin['getVisibilityItem'] } getVisibilityItem
 * @property { WebsitePageConfigOptionPlugin['getFooterVisibility'] } getFooterVisibility
 * @property { WebsitePageConfigOptionPlugin['doesPageOptionExist'] } doesPageOptionExist
 */

export class WebsitePageConfigOptionPlugin extends Plugin {
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
        on_target_shown_handlers: this.onTargetVisibilityToggle.bind(this, true),
        on_target_hidden_handlers: this.onTargetVisibilityToggle.bind(this, false),
        on_ready_to_save_document_handlers: this.onSave.bind(this),
    };

    /**
     * Returns the HTML element corresponding to the given type.
     *
     * @param {'header' | 'breadcrumb'} type The element type to retrieve.
     * @returns {HTMLElement | null} The matching element or null if not found.
     */
    getTarget(type) {
        const selector = TARGET_CONFIG[type]?.selector;
        return selector ? this.document.querySelector(selector) : null;
    }

    /**
     * Get the current visibility state of the target element.
     *
     * @param {'header' | 'breadcrumb'} type The target element type.
     * @returns {'regular' | 'overTheContent' | 'hidden'} The visibility state.
     */
    getVisibilityItem(type) {
        const el = this.getTarget(type);
        const isHidden = el.classList.contains("o_snippet_invisible");
        const targetConfig = TARGET_CONFIG[type];
        const isOverlay = this.document
            .querySelector(targetConfig.overlaySelector)
            .classList.contains(targetConfig.overlayClass);
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
     * @param {String | String[]} classPrefix Class prefix(es) to match (e.g.
     * "bg-" | "text-" | "o_cc")
     * @returns {String | null} Matching class name | hex color | null.
     */
    getColorValue(type, attribute, classPrefix) {
        const el = this.getTarget(type);
        const classPrefixes = Array.isArray(classPrefix) ? classPrefix : [classPrefix];
        const rawInlineValue = el.style.getPropertyValue(attribute).trim();
        const inlineValue = rawInlineValue ? rgbaToHex(rawInlineValue) : null;
        const colorCombinationClass = [...el.classList].find((cls) =>
            COLOR_COMBINATION_REGEX.test(cls)
        );
        if (classPrefixes.includes("o_cc")) {
            const pageOptionName = type === "header" ? "header_color" : "breadcrumb_color";
            const pageOptionInput = this.document.querySelector(
                `input.o_page_option_data[name='${pageOptionName}']`
            );
            const savedColorCombination = pageOptionInput?.value?.match(/\bo_cc[1-5]\b/)?.[0];
            const effectiveColorCombination = colorCombinationClass || savedColorCombination;
            if (effectiveColorCombination?.match(/^o_cc\d+$/)) {
                // Keep the color combination and optionally store the custom
                // override color with it.
                return inlineValue && inlineValue !== "#"
                    ? `${effectiveColorCombination}|${inlineValue}`
                    : effectiveColorCombination;
            }
        }
        const matchingClass =
            (classPrefixes.includes("o_cc") && colorCombinationClass) ||
            [...el.classList].find((cls) =>
                classPrefixes.some((prefix) => prefix && cls.startsWith(prefix))
            );
        return matchingClass || inlineValue;
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

        const pageOptions = {
            footer_visible: () => !this.getFooterVisibility(),
        };

        const headerEl = this.getTarget("header");
        if (headerEl) {
            const headerItem = this.getVisibilityItem("header");
            Object.assign(pageOptions, {
                header_overlay: () => headerItem === "overTheContent",
                header_color: () =>
                    headerItem === "overTheContent"
                        ? this.getColorValue("header", "background-color", ["o_cc", "bg-"])
                        : null,
                header_text_color: () =>
                    headerItem === "overTheContent"
                        ? this.getColorValue("header", "color", "text-")
                        : null,
                header_visible: () => headerItem !== "hidden",
            });
        }

        const breadcrumbEl = this.getTarget("breadcrumb");
        if (breadcrumbEl) {
            const breadcrumbItem = this.getVisibilityItem("breadcrumb");
            Object.assign(pageOptions, {
                breadcrumb_overlay: () => breadcrumbItem === "overTheContent",
                breadcrumb_color: () => this.getColorValue("breadcrumb", "background-color", "bg-"),
                breadcrumb_text_color: () => this.getColorValue("breadcrumb", "color", "text-"),
                breadcrumb_visible: () => breadcrumbItem !== "hidden",
            });
        }

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
        for (const { selector, action } of Object.values(TARGET_CONFIG)) {
            if (show && target.matches(selector)) {
                this.dependencies.builderActions.applyAction(action, {
                    editingElement: target,
                    value: "regular",
                    isPreviewing: false,
                });
            }
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
    static dependencies = ["websitePageConfigOptionPlugin", "domObserver", "visibility"];
    setup() {
        this.websitePageConfig = this.dependencies.websitePageConfigOptionPlugin;
        this.visibility = this.dependencies.visibility;
        this.domObserver = this.dependencies.domObserver;
        this.headerVisibilityHandlers = this.getVisibilityHandlers("header");
        this.breadcrumbVisibilityHandlers = this.getVisibilityHandlers("breadcrumb");
    }

    getVisibilityHandlers(type) {
        return {
            overTheContent: (colorPreset) => {
                this.setOverlay(type, true);
                this.setVisible(type, false);
                this.setColorCombination(type, colorPreset);
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
        const targetConfig = TARGET_CONFIG[type];
        const el = this.document.querySelector(targetConfig.overlaySelector);
        el.classList.toggle(targetConfig.overlayClass, shouldApply);
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
     * Find the theme preset that best matches the first section background
     * behind the header. If the section has a background image, its header
     * overlap area is averaged as a single color. Otherwise, the section color
     * preset is used, with white as final fallback.
     *
     * @returns {Promise<string|null>} The closest color preset class.
     */
    async getBestContrastPreset() {
        const firstSnippetEl = this.document.querySelector("#wrap > section[data-snippet]");
        if (!firstSnippetEl) {
            return null;
        }

        const sectionPreset = this.getPresetFromClassName(firstSnippetEl.className);
        const backgroundColor =
            (await getAverageBackgroundImageColor(
                firstSnippetEl,
                this.websitePageConfig.getTarget("header")
            )) ||
            this.getPresetBackgroundColor(this.getPresetNumber(sectionPreset)) ||
            WHITE_RGB;

        return this.getClosestPreset(backgroundColor);
    }

    getClosestPreset(color) {
        let bestPreset = null;
        let smallestDistance = Infinity;
        for (const preset of PRESET_NUMBERS) {
            const presetColor = this.getPresetBackgroundColor(preset);
            if (!presetColor) {
                continue;
            }
            const colorDistance =
                (presetColor.red - color.red) ** 2 +
                (presetColor.green - color.green) ** 2 +
                (presetColor.blue - color.blue) ** 2;
            if (colorDistance < smallestDistance) {
                smallestDistance = colorDistance;
                bestPreset = `o_cc${preset}`;
            }
        }
        return bestPreset;
    }

    /**
     * @param { String } className
     */
    getPresetFromClassName(className = "") {
        if (typeof className !== "string") {
            return null;
        }
        const match = className.match(/\bo_cc([1-5])\b/);
        return match ? `o_cc${match[1]}` : null;
    }

    /**
     * @param { String } presetClass
     */
    getPresetNumber(presetClass = "") {
        if (typeof presetClass !== "string") {
            return null;
        }
        const match = presetClass.match(/^o_cc([1-5])$/);
        return match ? parseInt(match[1], 10) : null;
    }

    /**
     * @param { String } cssColor
     */
    getRgbColor(cssColor = "", { blendOnWhite = false } = {}) {
        const rgba = convertCSSColorToRgba(cssColor);
        if (!rgba || rgba.opacity <= 0) {
            return null;
        }
        if (!blendOnWhite || rgba.opacity >= 100) {
            return { red: rgba.red, green: rgba.green, blue: rgba.blue };
        }
        const alpha = rgba.opacity / 100;
        return {
            red: Math.round(rgba.red * alpha + 255 * (1 - alpha)),
            green: Math.round(rgba.green * alpha + 255 * (1 - alpha)),
            blue: Math.round(rgba.blue * alpha + 255 * (1 - alpha)),
        };
    }

    /**
     * @param { Number } presetNumber
     */
    getPresetBackgroundColor(presetNumber) {
        if (!presetNumber) {
            return null;
        }
        const style = getComputedStyle(this.document.documentElement);
        let value = style.getPropertyValue(`--o-cc${presetNumber}-bg`).trim();
        const seen = new Set();
        while (value.startsWith("var(")) {
            const varName = value.match(/var\((--[^),\s]+)/)?.[1];
            if (!varName || seen.has(varName)) {
                break;
            }
            seen.add(varName);
            value = style.getPropertyValue(varName).trim();
        }
        return this.getRgbColor(value);
    }

    /**
     * Set the color combination class and set the background of the element
     * to transparent on the given target element.
     *
     * @param {'header' | 'breadcrumb'} type The element type to reset.
     * @param { String } colorPreset The color preset to apply.
     */
    setColorCombination(type, colorPreset) {
        if (!colorPreset) {
            return;
        }
        const el = this.websitePageConfig.getTarget(type);
        removeMatchingClasses(el, (cls) => cls.startsWith("bg-") || isColorCombinationClass(cls));
        el.classList.add("o_colored_level", "o_cc", colorPreset);
        el.style.setProperty("background-color", "rgba(0, 0, 0, 0)");
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
        removeMatchingClasses(
            el,
            (cls) => cls.startsWith("bg-o-color-") || isColorCombinationClass(cls)
        );
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
        removeMatchingClasses(el, (cls) => cls.startsWith("text-o-color-"));
    }
}
export class SetWebsiteHeaderVisibilityAction extends BaseWebsitePageConfigAction {
    static id = "setWebsiteHeaderVisibility";
    async apply({ editingElement, value: headerPositionValue, isPreviewing }) {
        const lastValue = this.websitePageConfig.getVisibilityItem("header");
        const headerEl = this.websitePageConfig.getTarget("header");
        const colorPreset =
            headerPositionValue === "overTheContent" ? await this.getBestContrastPreset() : null;
        const lastColorPreset =
            lastValue === "overTheContent" ? this.getPresetFromClassName(headerEl.className) : null;
        this.domObserver.applyCustomMutation({
            apply: () => this.headerVisibilityHandlers[headerPositionValue](colorPreset),
            revert: () => this.headerVisibilityHandlers[lastValue](lastColorPreset),
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
    apply({ value, isPreviewing }) {
        const lastValue = this.websitePageConfig.getVisibilityItem("breadcrumb");
        this.domObserver.applyCustomMutation({
            apply: () => this.breadcrumbVisibilityHandlers[value](),
            revert: () => this.breadcrumbVisibilityHandlers[lastValue](),
        });
        this.websitePageConfig.setDirty(isPreviewing);
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
