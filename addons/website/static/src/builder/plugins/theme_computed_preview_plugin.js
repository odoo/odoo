import { setBuilderCSSVariables } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import {
    AREA_GRADIENT_KEYS,
    AREAS,
    COLOR_FILES_URL,
    getUserColorKeys,
    NULL_VALUES,
    PALETTE_URL,
    PRINTED_NAMES,
    unquote,
    USER_VALUES_URL,
} from "./customize_website_plugin";

/**
 * @typedef { Object } ThemeComputedPreviewShared
 * @property { ThemeComputedPreviewPlugin['updatePreviewCopies'] } updatePreviewCopies
 */

// Theme settings that switch CSS rules on (`o-theme-gate` in the SCSS): the
// server marks the saved ones on `<html data-o-theme-gates>`. While a setting
// is previewed, its gate follows it:
// - `set`: on when the setting has a value (that `isOn`, if given, which can
//   read the other values);
// - `apart`: on when the setting differs from the one it otherwise follows;
// - `color`: on when the color is set (by the user or the palette).
export const THEME_GATES = {};
for (const key of [
    "headings-font-weight-bold",
    "display-font-weight-bold",
    "btn-font-weight-bold",
]) {
    THEME_GATES[key] = { set: key };
}
for (const side of ["top", "right", "bottom", "left"]) {
    THEME_GATES[`input-border-${side}-width`] = {
        apart: [`input-border-${side}-width`, "input-border-width"],
    };
}
for (const level of [
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "display-1",
    "display-2",
    "display-3",
    "display-4",
]) {
    THEME_GATES[`${level}-font`] = { apart: [`${level}-font`, "headings-font"] };
    if (level.startsWith("display")) {
        for (const property of ["line-height", "margin-top", "margin-bottom"]) {
            THEME_GATES[`${level}-${property}`] = {
                apart: [`${level}-${property}`, `headings-${property}`],
            };
        }
    }
}
for (const key of [
    "header-font-size",
    "menu-border-width",
    "menu-border-radius",
    "menu-shadow-class",
    "portal-card-border-width",
    "portal-card-border-radius",
]) {
    THEME_GATES[key] = { set: key };
}
THEME_GATES["header-bg-blur"] = { set: "header-bg-blur", isOn: (value) => value !== "0" };
THEME_GATES["navbar-font"] = { apart: ["navbar-font", "font"] };
THEME_GATES["header-text-color"] = { set: "header-text-color" };
THEME_GATES["body-image"] = { set: "body-image" };
// The button styles: Fill (also under Flat), Outline, Flat.
for (const which of ["primary", "secondary"]) {
    THEME_GATES[`btn-${which}-fill`] = {
        set: `btn-${which}-outline`,
        isOn: (value, getValue) => value !== "true" || getValue(`btn-${which}-flat`) === "true",
    };
    THEME_GATES[`btn-${which}-outline`] = {
        set: `btn-${which}-outline`,
        isOn: (value, getValue) => value === "true" && getValue(`btn-${which}-flat`) !== "true",
    };
    THEME_GATES[`btn-${which}-flat`] = {
        set: `btn-${which}-flat`,
        isOn: (value) => value === "true",
    };
}
THEME_GATES["link-underline-always"] = {
    set: "link-underline",
    isOn: (value) => unquote(value) === "always",
};
// The page layouts: Full, or Boxed and its variants Framed and Postcard.
THEME_GATES["layout-full"] = { set: "layout", isOn: (value) => unquote(value) === "full" };
THEME_GATES["layout-boxed"] = { set: "layout", isOn: (value) => unquote(value) !== "full" };
for (const layout of ["framed", "postcard"]) {
    THEME_GATES[`layout-${layout}`] = { set: "layout", isOn: (value) => unquote(value) === layout };
}
// The areas' custom colors and gradients (their presets are classes, see
// `updateAreaClasses`).
for (const area of AREAS) {
    THEME_GATES[`${area}-custom`] = { color: `${area}-custom` };
}
for (const gradient of [...AREA_GRADIENT_KEYS, "portal-gradient"]) {
    THEME_GATES[gradient] = { set: gradient };
}
for (let i = 1; i <= 5; i++) {
    for (const key of ["headings", "h2", "h3", "h4", "h5", "h6"]) {
        THEME_GATES[`o-cc${i}-${key}`] = { color: `o-cc${i}-${key}` };
    }
    THEME_GATES[`o-cc${i}-bg-gradient`] = { set: `o-cc${i}-bg-gradient` };
}
// The elements of each area, as `o-area-colors` gets them in the SCSS: the
// builder marks them with `data-o-cc-area` while it previews the area's color
// preset, which they then get as a class (see `updateAreaClasses`).
export const AREA_SELECTORS = {
    menu: "#wrapwrap > header .navbar-light",
    "header-sales_one": "#wrapwrap .o_header_sales_one_bot",
    "header-sales_two": "#wrapwrap .o_header_sales_two_top",
    "header-sales_three": "#wrapwrap .o_header_sales_three_top",
    "header-sales_four": "#wrapwrap .o_header_sales_four_bot",
    footer: ".o_footer",
    copyright: ".o_footer .o_footer_copyright",
    breadcrumb: "#wrapwrap > main:not(.o_breadcrumb_overlay) div.o_page_breadcrumb nav",
    "portal-card": ".o_portal_index_card > a:not(.alert)",
};
const PRESET_CLASSES = ["o_cc1", "o_cc2", "o_cc3", "o_cc4", "o_cc5"];
const THEME_GATES_ATTRIBUTE = "data-o-theme-gates";

/**
 * What the page computes from the previewed theme values (see
 * `customizeWebsite`), beyond the values themselves: the theme gates, the areas'
 * preset classes, the colors the compile derives (through the server), and the
 * copies of it all in the builder. Follows the previewed values, not part of
 * the history.
 */
export class ThemeComputedPreviewPlugin extends Plugin {
    static id = "themeComputedPreview";
    static dependencies = ["customizeWebsite", "domObserver", "history"];
    static shared = ["updatePreviewCopies"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_theme_preview_changed_handlers: (state) => {
            this.updateThemeGates();
            this.updateAreaClasses();
            this.updatePreviewCopies();
            if (
                Object.entries(state).some(
                    ([name, { file }]) =>
                        file?.startsWith(COLOR_FILES_URL) || name === "color-palettes-name"
                )
            ) {
                this.updateComputedColors();
            }
        },
        // A new part of the page shows the previewed area presets too.
        on_chrome_replaced_handlers: () => this.updateAreaClasses(),
        clean_for_save_processors: (root) => {
            this.cleanAreaClasses(root);
            return root;
        },
    };

    /** @type {Set<string>} the theme gates of the saved values */
    savedThemeGates;
    /** @type {Set<string>} the computed colors set on the root (see `updateComputedColors`) */
    computedColorNames = new Set();
    /** @type {Object<string, boolean>} the theme gates computed from the colors */
    computedGates = {};
    computedColorsRequestId = 0;

    setup() {
        this.savedThemeGates = new Set(
            (this.document.documentElement.getAttribute(THEME_GATES_ATTRIBUTE) || "")
                .split(" ")
                .filter(Boolean)
        );
    }
    /**
     * Previews the areas' color presets (header, footer...): their elements get
     * the preset as a class, marked `data-o-cc-area` so that the compiled
     * preset stops applying to them (see `o-area-colors`), while the preset is
     * previewed (or a palette switch). No preset: marked, without a class.
     * Not edits of the page: not recorded.
     */
    updateAreaClasses() {
        const { getPendingValues, getWebsiteVariableValue } = this.dependencies.customizeWebsite;
        const pendingPalette = getPendingValues(PALETTE_URL);
        const isPaletteSwitched = "color-palettes-name" in getPendingValues(USER_VALUES_URL);
        const updates = [];
        for (const [area, selector] of Object.entries(AREA_SELECTORS)) {
            // A preset's number, "" for none, false when not previewed.
            const isPreviewed = area in pendingPalette || isPaletteSwitched;
            const value = isPreviewed && getWebsiteVariableValue(area);
            const preset = isPreviewed && (/^[1-5]$/.test(value) ? value : "");
            for (const el of this.document.querySelectorAll(selector)) {
                // The element's preview, as `preset`.
                const elPreset =
                    !!el.dataset.oCcArea &&
                    (PRESET_CLASSES.find((cls) => el.classList.contains(cls))?.slice(-1) || "");
                if (elPreset !== preset) {
                    updates.push([el, area, preset]);
                }
            }
        }
        if (!updates.length) {
            // `ignore` also records the pending mutations: within an edit,
            // marking its element dirty out of the history (see `SavePlugin`).
            return;
        }
        this.dependencies.domObserver.ignore(() => {
            for (const [el, area, preset] of updates) {
                if (el.dataset.oCcArea) {
                    el.classList.remove(...PRESET_CLASSES);
                    delete el.dataset.oCcArea;
                }
                if (preset !== false) {
                    if (preset) {
                        el.classList.add(`o_cc${preset}`);
                    }
                    el.dataset.oCcArea = area;
                }
            }
        });
    }
    /**
     * @param {HTMLElement} root
     */
    cleanAreaClasses(root) {
        for (const el of selectElements(root, "[data-o-cc-area]")) {
            el.classList.remove(...PRESET_CLASSES);
            delete el.dataset.oCcArea;
        }
    }
    /**
     * Turns the theme gates of the previewed settings on or off (the others
     * keep their saved state). Computed from the current values, so they
     * follow undo and redo without being part of the history steps.
     */
    updateThemeGates() {
        const { getPendingValues, getWebsiteVariableValue, getWebsiteVariableDefault } =
            this.dependencies.customizeWebsite;
        const pendingValues = getPendingValues(USER_VALUES_URL);
        const pendingPalette = getPendingValues(PALETTE_URL);
        const isPaletteSwitched = "color-palettes-name" in pendingValues;
        // The previewed gates, on or off.
        const states = {};
        for (const [gate, { set, isOn, apart, color }] of Object.entries(THEME_GATES)) {
            if (color) {
                if (color in pendingPalette || isPaletteSwitched) {
                    // A color reset to `null` is the palette's, if any.
                    const value = pendingPalette[color];
                    states[gate] =
                        value === undefined || value === "null"
                            ? !!getWebsiteVariableDefault(color)
                            : !NULL_VALUES.includes(value);
                }
            } else if (set) {
                if (set in pendingValues) {
                    const value = pendingValues[set];
                    states[gate] =
                        !NULL_VALUES.includes(value) &&
                        (!isOn || isOn(value, getWebsiteVariableValue));
                }
            } else if (apart.some((name) => name in pendingValues)) {
                states[gate] =
                    getWebsiteVariableValue(apart[0]) !== getWebsiteVariableValue(apart[1]);
            }
        }
        Object.assign(states, this.computedGates);
        const gates = new Set(this.savedThemeGates);
        for (const [gate, isOn] of Object.entries(states)) {
            if (isOn) {
                gates.add(gate);
            } else {
                gates.delete(gate);
            }
        }
        this.document.documentElement.setAttribute(THEME_GATES_ATTRIBUTE, [...gates].join(" "));
    }
    /**
     * While colors are previewed, sets the colors the compile computes from
     * them (readable text and links, buttons' states...) on the root, as the
     * server computes them (see `color_system.py`). Not part of the history:
     * recomputed after the preview changes, the latest answer wins.
     */
    updateComputedColors = debounce(this._updateComputedColors.bind(this), 0);
    async _updateComputedColors() {
        const requestId = ++this.computedColorsRequestId;
        let values = {};
        let gates = {};
        if (this.dependencies.customizeWebsite.isPreviewingColors()) {
            ({ values, gates } = await rpc(
                "/website/theme_computed_colors",
                this.getComputedColorsInputs(),
                { silent: true }
            ));
            if (requestId !== this.computedColorsRequestId || this.isDestroyed) {
                return;
            }
        }
        const style = this.document.documentElement.style;
        for (const name of this.computedColorNames) {
            if (!(name in values)) {
                style.removeProperty(`--${name}`);
            }
        }
        for (const [name, value] of Object.entries(values)) {
            style.setProperty(`--${name}`, value);
        }
        this.computedColorNames = new Set(Object.keys(values));
        this.computedGates = gates;
        this.updateThemeGates();
        this.updatePreviewCopies();
        // The options showing these colors (e.g. a preset's text) follow, but
        // not a hovered color: the panel shows the applied one.
        if (!this.dependencies.history.getIsPreviewing()) {
            this.trigger("on_dom_updated_handlers");
        }
    }
    /**
     * @returns {Object} what the server computes the colors from: the colors
     *          as currently shown, and which ones are set
     */
    getComputedColorsInputs() {
        const style = getHtmlStyle(this.document);
        const get = (name) => getCSSVariableValue(name, style);
        const pendingPalette = this.dependencies.customizeWebsite.getPendingValues(PALETTE_URL);
        const userKeys = new Set(getUserColorKeys(style));
        for (const [name, value] of Object.entries(pendingPalette)) {
            if (NULL_VALUES.includes(value)) {
                userKeys.delete(name);
            } else {
                userKeys.add(name);
            }
        }
        const isSet = (name) =>
            userKeys.has(name) ||
            !!this.dependencies.customizeWebsite.getWebsiteVariableDefault(name);
        const colors = {};
        for (const name of [
            ...["100", "200", "300", "400", "500", "600", "700", "800", "900", "white", "black"],
            ...["primary", "secondary", "success", "info", "warning", "danger", "light", "dark"],
            ...["o-color-1", "o-color-2", "o-color-3", "o-color-4", "o-color-5"],
        ]) {
            colors[name] = get(name);
        }
        for (const name of ["input", "body"].filter(isSet)) {
            colors[name] = get(name);
        }
        for (let i = 1; get(`o-cc${i}-bg`); i++) {
            colors[`o-cc${i}-bg`] = get(`o-cc${i}-bg`);
            for (const key of [
                "text",
                "link",
                "btn-primary",
                "btn-primary-border",
                "btn-secondary",
                "btn-secondary-border",
            ]) {
                const name = `o-cc${i}-${key}`;
                if (isSet(name)) {
                    colors[name] = get(PRINTED_NAMES[name] || name);
                }
            }
        }
        // The areas (header, footer...): their color preset, their custom
        // color if set.
        const areas = {};
        for (const area of AREAS) {
            areas[area] = get(area);
            if (isSet(`${area}-custom`)) {
                colors[`${area}-custom`] = get(`${area}-custom`);
            }
        }
        return {
            colors,
            areas,
            user_keys: [...userKeys],
            min_contrast_ratio: parseFloat(get("o-min-contrast-ratio")),
        };
    }
    /**
     * Copies the previewed values to the colors preview dialog's page and to
     * the builder's own copies of the colors (color picker).
     */
    updatePreviewCopies() {
        const htmlEl = this.document.documentElement;
        const previewHtmlEl = this.config.extraPreviewDocument?.documentElement;
        if (previewHtmlEl) {
            previewHtmlEl.style.cssText = htmlEl.style.cssText;
            previewHtmlEl.setAttribute(
                THEME_GATES_ATTRIBUTE,
                htmlEl.getAttribute(THEME_GATES_ATTRIBUTE) || ""
            );
        }
        setBuilderCSSVariables(getHtmlStyle(this.document));
    }
}

registry.category("website-plugins").add(ThemeComputedPreviewPlugin.id, ThemeComputedPreviewPlugin);
