import {
    isCSSVariable,
    setBuilderCSSVariables,
    getBgImageURLFromEl,
} from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { parseHTML } from "@html_editor/utils/html";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { isColorGradient, isCSSColor } from "@web/core/utils/colors";
import { debounce } from "@web/core/utils/timing";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { renderToElement } from "@web/core/utils/render";
import { CompositeAction } from "@html_builder/core/composite_action_plugin";
import { ImagePositionOverlay } from "@html_builder/plugins/image/image_position_overlay";
import { loadImage } from "@html_editor/utils/image_processing";

/**
 * @typedef { Object } CustomizeWebsiteShared
 * @property { CustomizeWebsitePlugin['customizeWebsiteColors'] } customizeWebsiteColors
 * @property { CustomizeWebsitePlugin['customizeWebsiteVariables'] } customizeWebsiteVariables
 * @property { CustomizeWebsitePlugin['previewWebsiteVariables'] } previewWebsiteVariables
 * @property { CustomizeWebsitePlugin['previewWebsiteColors'] } previewWebsiteColors
 * @property { CustomizeWebsitePlugin['previewColorPalette'] } previewColorPalette
 * @property { CustomizeWebsitePlugin['hasCustomizedColors'] } hasCustomizedColors
 * @property { CustomizeWebsitePlugin['loadTemplateKey'] } loadTemplateKey
 * @property { CustomizeWebsitePlugin['makeSCSSCusto'] } makeSCSSCusto
 * @property { CustomizeWebsitePlugin['toggleTemplate'] } toggleTemplate
 * @property { CustomizeWebsitePlugin['withCustomHistory'] } withCustomHistory
 * @property { CustomizeWebsitePlugin['populateCache'] } populateCache
 * @property { CustomizeWebsitePlugin['loadConfigKey'] } loadConfigKey
 * @property { CustomizeWebsitePlugin['getConfigKey'] } getConfigKey
 * @property { CustomizeWebsitePlugin['getWebsiteVariableValue'] } getWebsiteVariableValue
 * @property { CustomizeWebsitePlugin['getWebsiteVariableDefault'] } getWebsiteVariableDefault
 * @property { CustomizeWebsitePlugin['updatePreviewCopies'] } updatePreviewCopies
 * @property { CustomizeWebsitePlugin['getPendingThemeRequests'] } getPendingThemeRequests
 * @property { CustomizeWebsitePlugin['setPendingThemeRequests'] } setPendingThemeRequests
 * @property { CustomizeWebsitePlugin['isPluginDestroyed'] } isPluginDestroyed
 * @property { CustomizeWebsitePlugin['reloadBundles'] } reloadBundles
 * @property { CustomizeWebsitePlugin['setViewsOnSave'] } setViewsOnSave
 */

/**
 * @typedef {((colors: string[]) => void)[]} on_website_color_updated_handlers
 */

export const NO_IMAGE_SELECTION = Symbol.for("NoImageSelection");
const USER_VALUES_URL = "/website/static/src/scss/options/user_values.scss";
// Theme values that Bootstrap also names the button's own variables after:
// `website.scss` prints them under another name, the one the CSS reads.
const PRINTED_NAMES = {
    "btn-padding-x": "o-btn-padding-x",
    "btn-padding-y": "o-btn-padding-y",
    "btn-font-size": "o-btn-font-size",
    "btn-border-radius": "o-btn-border-radius",
    "btn-font-weight": "o-btn-font-weight",
};
// Theme settings that switch CSS rules on (`o-theme-gate` in the SCSS): the
// server marks the saved ones on `<html data-o-theme-gates>`. While a setting
// is previewed, its gate follows it:
// - `set`: on when the setting has a value (that `isOn`, if given);
// - `apart`: on when the setting differs from the one it otherwise follows;
// - `color`: on when the color is set (by the user or the palette).
const THEME_GATES = {};
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
// The button styles: Fill (also under Flat), Outline, Flat.
for (const which of ["primary", "secondary"]) {
    THEME_GATES[`btn-${which}-fill`] = {
        set: `btn-${which}-outline`,
        isOn: (value) => value !== "true",
    };
    THEME_GATES[`btn-${which}-outline`] = {
        set: `btn-${which}-outline`,
        isOn: (value) => value === "true",
    };
    THEME_GATES[`btn-${which}-flat`] = {
        set: `btn-${which}-flat`,
        isOn: (value) => value === "true",
    };
}
const unquote = (value) => value.replace(/^'(.*)'$/, "$1");
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
for (const area of [
    ...["menu", "header-sales_one", "header-sales_two", "header-sales_three"],
    ...["header-sales_four", "footer", "copyright", "breadcrumb", "portal-card"],
]) {
    THEME_GATES[`${area}-custom`] = { color: `${area}-custom` };
}
for (const gradient of [
    ...["menu-gradient", "menu-secondary-gradient", "footer-gradient"],
    ...["copyright-gradient", "breadcrumb-gradient", "portal-gradient"],
]) {
    THEME_GATES[gradient] = { set: gradient };
}
const COLOR_FILES_URL = "/website/static/src/scss/options/colors/";
const PALETTE_URL = `${COLOR_FILES_URL}user_color_palette.scss`;
const THEME_PALETTE_URL = `${COLOR_FILES_URL}user_theme_color_palette.scss`;
// Saved after the user values (a palette switch resets them), in this order.
const COLOR_FILE_URLS = [
    PALETTE_URL,
    THEME_PALETTE_URL,
    `${COLOR_FILES_URL}user_gray_color_palette.scss`,
];
for (let i = 1; i <= 5; i++) {
    for (const key of ["headings", "h2", "h3", "h4", "h5", "h6"]) {
        THEME_GATES[`o-cc${i}-${key}`] = { color: `o-cc${i}-${key}` };
    }
    THEME_GATES[`o-cc${i}-bg-gradient`] = { set: `o-cc${i}-bg-gradient` };
    // html_editor prints the links made readable under their names.
    PRINTED_NAMES[`o-cc${i}-link`] = `o-cc${i}-link-base`;
}
/**
 * What a color of a color combination reads when not set (see html_editor's
 * `:root` prints).
 *
 * @param {string} name
 */
function getColorFallback(name) {
    const [, cc, key] = name.match(/^(o-cc\d+)-(.+)$/) || [];
    const fallback = {
        text: `${cc}-bg-contrast`,
        headings: `${cc}-text`,
        h2: `${cc}-headings`,
        h3: `${cc}-headings`,
        h4: `${cc}-headings`,
        h5: `${cc}-headings`,
        h6: `${cc}-headings`,
        "btn-primary": "primary",
        "btn-primary-border": `${cc}-btn-primary`,
        "btn-secondary": "secondary",
        "btn-secondary-border": `${cc}-btn-secondary`,
    }[key];
    return fallback ? `var(--${fallback})` : "";
}
const THEME_GATES_ATTRIBUTE = "data-o-theme-gates";
const NULL_VALUES = ["null", "NULL", "''"];

export class CustomizeWebsitePlugin extends Plugin {
    static id = "customizeWebsite";
    static dependencies = ["builderActions", "domObserver", "savePlugin", "edit_interaction", "websiteBridge"];
    static shared = [
        "customizeWebsiteColors",
        "customizeWebsiteVariables",
        "previewWebsiteVariables",
        "previewWebsiteColors",
        "previewColorPalette",
        "hasCustomizedColors",
        "loadTemplateKey",
        "makeSCSSCusto",
        "toggleTemplate",
        "withCustomHistory",
        "populateCache",
        "loadConfigKey",
        "getConfigKey",
        "getWebsiteVariableValue",
        "getWebsiteVariableDefault",
        "updatePreviewCopies",
        "getPendingThemeRequests",
        "setPendingThemeRequests",
        "isPluginDestroyed",
        "reloadBundles",
        "setViewsOnSave",
    ];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            CustomizeWebsiteVariableAction,
            PreviewWebsiteVariableAction,
            CustomizeWebsiteSubVariablesAction,
            PreviewWebsiteSubVariablesAction,
            ResetWebsiteVariablesAction,
            CustomizeWebsiteColorAction,
            PreviewWebsiteColorAction,
            SwitchThemeAction,
            AddLanguageAction,
            CustomizeButtonStyleAction,
            PreviewButtonStyleAction,
            PreviewLinkStyleAction,
            PreviewAreaColorAction,
            WebsiteConfigAction,
            PreviewableWebsiteConfigAction,
            TemplatePreviewableWebsiteConfigAction,
            SelectTemplateAction,
            ToggleBodyBgImageAction,
            ReplaceBodyBgImageAction,
            RemoveBodyBgImageAction,
            BodyBgPositionOverlayAction,
        },
        color_combination_providers: withSequence(5, (el, actionParam) => {
            const combination = actionParam.combinationColor;
            if (combination) {
                const style = getHtmlStyle(this.document);
                return `o_cc${getCSSVariableValue(combination, style)}`;
            }
        }),
        on_ready_to_save_document_handlers: this.onSave.bind(this),

        // Previewed values (see `previewWebsiteVariables`) are history commit
        // data: each step holds the previous and next state to apply.
        history_commit_data_properties: ["themePreview"],
        pending_history_commit_data_processors: (data) =>
            this.pendingPreviewSteps.length
                ? { ...data, themePreview: [...this.pendingPreviewSteps] }
                : data,
        on_committed_to_history_handlers: () => {
            this.pendingPreviewSteps = [];
        },
        has_history_commit_changes_predicates: (commit) => {
            if (commit.data.themePreview?.length) {
                return true;
            }
        },
        // Like the DOM mutations, `ensureNewMutations` records what is applied
        // or reverted as new changes (e.g. in the undo commit, which is what
        // redo reverts).
        on_apply_history_commit_handlers: (commit, { ensureNewMutations = false } = {}) => {
            for (const step of commit.data.themePreview || []) {
                this.setPreviewState(step.next);
                if (ensureNewMutations) {
                    this.pendingPreviewSteps.push(step);
                }
            }
        },
        on_revert_history_commit_handlers: (commit, { ensureNewMutations = false } = {}) => {
            for (const step of [...(commit.data.themePreview || [])].reverse()) {
                this.setPreviewState(step.previous);
                if (ensureNewMutations) {
                    this.pendingPreviewSteps.push({ previous: step.next, next: step.previous });
                }
            }
        },
        on_will_invalidate_pending_changes_handlers: () => {
            for (const step of this.pendingPreviewSteps.reverse()) {
                this.setPreviewState(step.previous);
            }
            this.pendingPreviewSteps = [];
        },
        on_pending_changes_unstashed_handlers: (stashedCommit) => {
            this.pendingPreviewSteps.push(...(stashedCommit.data.themePreview || []));
        },
        save_point_history_commit_data_processors: (data) => ({
            ...data,
            themePreview: [...this.pendingPreviewSteps],
        }),
        on_savepoint_restored_handlers: (savePoint) => {
            for (const step of savePoint.data.themePreview) {
                this.setPreviewState(step.next);
            }
            this.pendingPreviewSteps.push(...savePoint.data.themePreview);
        },
    };

    async onSave() {
        if (this.viewsToEnableOnSave.size || this.viewsToDisableOnSave.size) {
            await rpc("/website/theme_customize_data", {
                is_view_data: true,
                enable: [...this.viewsToEnableOnSave],
                disable: [...this.viewsToDisableOnSave],
                reset_view_arch: false,
            });
        }
        // No bundle reload: the iframe is reloaded after save.
        for (const url of [USER_VALUES_URL, ...COLOR_FILE_URLS]) {
            const values = this.getPendingValues(url);
            if (Object.keys(values).length) {
                await this.makeSCSSCusto(url, values);
            }
        }
    }
    cache = {};
    activeRecords = {};
    activeTemplateViews = {};
    viewsToEnableOnSave = new Set();
    viewsToDisableOnSave = new Set();
    pendingViewRequests = new Set();
    pendingAssetRequests = new Set();
    /**
     * @typedef {{
     *  isViewData: boolean,
     *  shouldReset: boolean,
     *  toEnable: Set<string>,
     *  toDisable: Set<string>,
     *  def: Deferred,
     * }} pendingThemeRequest
     */
    /**
     * @type pendingThemeRequest[]
     */
    pendingThemeRequests = [];
    variablesToCustomize = {};
    /** @type {Object<string, string>} values to write in `user_values.scss` on save */
    pendingVariables = {};
    /** @type {Object<string, Object<string, string>>} colors to write on save, by file */
    pendingColors = {};
    /** Preview steps not committed to the history yet. */
    pendingPreviewSteps = [];
    /** @type {Set<string>} the theme gates of the saved values */
    savedThemeGates;
    /** @type {Set<string>} the computed colors set on the root (see `updateComputedColors`) */
    computedColorNames = new Set();
    /** @type {Object<string, boolean>} the theme gates computed from the colors */
    computedGates = {};
    computedColorsRequestId = 0;
    colorsToCustomize = {};
    resolves = {};
    getPendingThemeRequests() {
        return this.pendingThemeRequests;
    }
    setPendingThemeRequests(pendingThemeRequests) {
        this.pendingThemeRequests = pendingThemeRequests;
    }
    getWebsiteVariableValue(variable) {
        const style = getHtmlStyle(this.document);
        let finalValue = getCSSVariableValue(PRINTED_NAMES[variable] || variable, style);
        /* TODO dedicated action ?
        if (!params.colorNames) {
            return finalValue;
        }
        */
        let tempValue = finalValue;
        while (tempValue) {
            finalValue = tempValue;
            if (tempValue !== "" && Number.isFinite(Number(tempValue))) {
                // the CSS variable value is a number and not a variable name.
                break;
            }
            tempValue = getCSSVariableValue(tempValue.replaceAll("'", ""), style);
            if (tempValue === finalValue) {
                // the CSS variable value is identical to its name.
                break;
            }
        }
        // Unquote value
        if (finalValue.startsWith(`'`)) {
            finalValue = finalValue.substring(1, finalValue.length - 1);
        }
        return finalValue;
    }
    /**
     * The value a website variable resets to, if the compiled CSS prints it
     * (as `--o-default-<variable>`).
     *
     * @param {string} variable
     * @returns {string|undefined}
     */
    getWebsiteVariableDefault(variable) {
        return (
            getCSSVariableValue(`o-default-${variable}`, getHtmlStyle(this.document)) || undefined
        );
    }
    async customizeWebsiteVariables(
        variables = {},
        nullValue = "null",
        clean = false,
        reloadBundles = true
    ) {
        this.variablesToCustomize = Object.assign(this.variablesToCustomize, variables);
        if (!Object.keys(this.variablesToCustomize).length) {
            return;
        }
        if (clean) {
            for (const variable in variables) {
                this.variablesToCustomize[variable] = nullValue;
            }
        }
        await this.debouncedSCSSVariablesCusto(nullValue);
        if (reloadBundles) {
            await this.reloadBundles();
        }
    }
    /**
     * Previews website variables by overriding their printed value inline on
     * the iframe root, where both `getWebsiteVariableValue` and the compiled
     * CSS read it. Only works for the variables the compiled CSS reads through
     * `var()`. The SCSS customization is only written on save.
     *
     * A reset (empty value, or `nullValue`) previews the default, if printed
     * (see `getWebsiteVariableDefault`), else removes the override: the last
     * saved value shows until save.
     *
     * @param {Object<string, string>} variables
     * @param {string} [nullValue="null"]
     * @param {Object<string, string>} [previewValues] values set on the root
     *        but never written, e.g. a font's family next to its name. For a
     *        name also in `variables`, what to show instead of its value.
     */
    previewWebsiteVariables(variables, nullValue = "null", previewValues = {}) {
        const style = this.document.documentElement.style;
        const step = { previous: {}, next: {} };
        for (const name of new Set([...Object.keys(variables), ...Object.keys(previewValues)])) {
            step.previous[name] = {
                pending: this.pendingVariables[name],
                inline: style.getPropertyValue(`--${PRINTED_NAMES[name] || name}`),
            };
            const value = variables[name] === nullValue ? "" : variables[name];
            step.next[name] = {
                pending: name in variables ? value || nullValue : this.pendingVariables[name],
                inline: previewValues[name] ?? (value || this.getDefaultInlineValue(name)),
            };
        }
        // The root is outside the observed editable: the step goes to the
        // history as commit data, which reverts hover previews and undo.
        this.setPreviewState(step.next);
        this.pendingPreviewSteps.push(step);
    }
    /**
     * Refers to the default rather than copying it: a default that is another
     * value (e.g. a heading level's, the headings one) keeps following it.
     *
     * @param {string} name
     */
    getDefaultInlineValue(name) {
        return this.getWebsiteVariableDefault(name) ? `var(--o-default-${name})` : "";
    }
    /**
     * Same as `previewWebsiteVariables`, for colors (written in their own
     * files). A color given as another one's name follows it. A reset
     * previews what the color falls back to: the palette's, else the one
     * it reads when not set (see `getColorFallback`).
     *
     * The colors computed from them follow, see `updateComputedColors`.
     *
     * @param {Object<string, string>} colors
     * @param {Object} [options]
     * @param {string} [options.colorType] the file: "theme", "gray", or the
     *        palette's by default
     * @param {string} [options.nullValue="null"]
     */
    previewWebsiteColors(colors, { colorType, nullValue = "null" } = {}) {
        const file = `${COLOR_FILES_URL}user_${colorType ? colorType + "_" : ""}color_palette.scss`;
        const pendingValues = this.getPendingValues(file);
        const style = this.document.documentElement.style;
        const step = { previous: {}, next: {} };
        for (const [name, color] of Object.entries(colors)) {
            const value = color && this.getSCSSColorValue(color);
            step.previous[name] = {
                file,
                pending: pendingValues[name],
                inline: style.getPropertyValue(`--${PRINTED_NAMES[name] || name}`),
            };
            step.next[name] = {
                file,
                pending: value || nullValue,
                inline: value
                    ? value.replace(/^'(.*)'$/, "var(--$1)")
                    : this.getDefaultInlineValue(name) || getColorFallback(name),
            };
        }
        this.setPreviewState(step.next);
        this.pendingPreviewSteps.push(step);
    }
    /**
     * Previews a palette switch: the palette's colors replace the colors (on
     * save, the server resets the user's colors when it writes the palette's
     * name, and the colors changed afterwards are written after it). The
     * palettes' colors are printed in the builder's document (see
     * `color_palettes.scss`).
     *
     * @param {string} paletteName
     */
    previewColorPalette(paletteName) {
        const builderStyle = getComputedStyle(document.documentElement);
        const getPaletteValue = (key) =>
            getCSSVariableValue(`o-palette-${paletteName}-${key}`, builderStyle);
        // A color as CSS: a color's name reads it. An area's color preset is
        // a number (see `website.scss`'s prints).
        const toCSS = (value) => {
            value = value.replace(/^'(.*)'$/, "$1");
            return value && !isCSSColor(value) && !/^\d+$/.test(value) ? `var(--${value})` : value;
        };
        const style = this.document.documentElement.style;
        const step = { previous: {}, next: {} };
        const add = (name, file, pending, inline) => {
            step.previous[name] = {
                file,
                pending: this.getPendingValues(file)[name],
                inline: style.getPropertyValue(`--${PRINTED_NAMES[name] || name}`),
            };
            step.next[name] = { file, pending, inline };
        };
        add("color-palettes-name", USER_VALUES_URL, `'${paletteName}'`, `'${paletteName}'`);
        // Reset by the server too.
        for (let i = 1; i <= 5; i++) {
            add(`o-cc${i}-bg-gradient`, USER_VALUES_URL, "null", "");
        }
        for (const key of [
            ...["menu-gradient", "menu-secondary-gradient", "footer-gradient"],
            ...["copyright-gradient", "breadcrumb-gradient"],
        ]) {
            add(key, USER_VALUES_URL, "null", "");
        }
        // No user color anymore: a color is the palette's (its default).
        add("o-user-color-keys", USER_VALUES_URL, undefined, '""');
        const keys = getCSSVariableValue("o-palette-keys", builderStyle).replace(/['"]/g, "");
        for (const key of keys.split(" ").filter(Boolean)) {
            const value = toCSS(
                getPaletteValue(key) || getCSSVariableValue(`o-base-palette-${key}`, builderStyle)
            );
            add(`o-default-${key}`, PALETTE_URL, undefined, value || "initial");
            add(
                key,
                PALETTE_URL,
                undefined,
                value ? `var(--o-default-${key})` : getColorFallback(key)
            );
        }
        for (const key of ["success", "info", "warning", "danger"]) {
            const value = toCSS(getPaletteValue(key)) || `var(--o-base-theme-${key})`;
            add(`o-default-${key}`, THEME_PALETTE_URL, undefined, value);
            add(key, THEME_PALETTE_URL, undefined, `var(--o-default-${key})`);
        }
        const grayURL = `${COLOR_FILES_URL}user_gray_color_palette.scss`;
        for (let i = 100; i <= 900; i += 100) {
            const value = getPaletteValue(`${i}`) || getCSSVariableValue(`base-${i}`, builderStyle);
            add(`${i}`, grayURL, undefined, value);
        }
        this.setPreviewState(step.next);
        this.pendingPreviewSteps.push(step);
    }
    /**
     * Whether a palette switch would reset color customizations (palette
     * colors and status colors, as `$o-has-customized-colors`): the saved
     * ones, unless a palette switch is pending (it resets them already), and
     * the pending ones.
     *
     * @returns {boolean}
     */
    hasCustomizedColors() {
        const isSet = (value) => value !== undefined && !NULL_VALUES.includes(value);
        const savedValue = getCSSVariableValue(
            "has-customized-colors",
            getComputedStyle(this.document.body)
        );
        const statusColors = this.getPendingValues(THEME_PALETTE_URL);
        return (
            (!("color-palettes-name" in this.pendingVariables) &&
                !!savedValue &&
                savedValue !== "false") ||
            Object.values(this.getPendingValues(PALETTE_URL)).some(isSet) ||
            ["success", "info", "warning", "danger"].some((key) => isSet(statusColors[key]))
        );
    }
    /**
     * @param {string} color a color, a color's name or a CSS variable
     * @returns {string} the color as written in a colors file: a name is
     *          quoted, a CSS variable is its value
     */
    getSCSSColorValue(color) {
        if (/^\d+$/.test(color)) {
            // A color preset's number.
            return color;
        }
        if (isCSSVariable(color)) {
            return this.getWebsiteVariableValue(color.match(/var\(--(.+?)\)/)[1]);
        }
        return isCSSColor(color) ? color : `'${color}'`;
    }
    /**
     * @param {string} file
     * @returns {Object<string, string>} the values to write in it on save
     */
    getPendingValues(file) {
        if (file === USER_VALUES_URL) {
            return this.pendingVariables;
        }
        return (this.pendingColors[file] ??= {});
    }
    setPreviewState(state) {
        const style = this.document.documentElement.style;
        for (const [name, { pending, inline, file = USER_VALUES_URL }] of Object.entries(state)) {
            const pendingValues = this.getPendingValues(file);
            if (pending === undefined) {
                delete pendingValues[name];
            } else {
                pendingValues[name] = pending;
            }
            const printedName = PRINTED_NAMES[name] || name;
            if (inline) {
                style.setProperty(`--${printedName}`, inline);
            } else {
                style.removeProperty(`--${printedName}`);
            }
        }
        this.updateThemeGates();
        this.updateAreaClasses();
        this.updatePreviewCopies();
        this.updateComputedColors();
    }
    /**
     * Sets the areas' color preset classes (`o_cc<N>`, rendered by the server
     * on the elements marked `data-o-cc-area`) to their previewed presets.
     * Not edits of the page: not recorded.
     */
    updateAreaClasses() {
        this.dependencies.domObserver.ignore(() => {
            for (const el of this.document.querySelectorAll("[data-o-cc-area]")) {
                const preset = this.getWebsiteVariableValue(el.dataset.oCcArea);
                if (/^[1-5]$/.test(preset)) {
                    el.classList.remove("o_cc1", "o_cc2", "o_cc3", "o_cc4", "o_cc5");
                    el.classList.add(`o_cc${preset}`);
                }
            }
        });
    }
    /**
     * Turns the theme gates of the previewed settings on or off (the others
     * keep their saved state). Computed from the current values, so they
     * follow undo and redo without being part of the history steps.
     */
    updateThemeGates() {
        const htmlEl = this.document.documentElement;
        this.savedThemeGates ??= new Set(
            (htmlEl.getAttribute(THEME_GATES_ATTRIBUTE) || "").split(" ").filter(Boolean)
        );
        const gates = new Set(this.savedThemeGates);
        const pendingPalette = this.getPendingValues(PALETTE_URL);
        const isPaletteSwitched = "color-palettes-name" in this.pendingVariables;
        for (const [gate, { set, isOn: isValueOn, apart, color }] of Object.entries(THEME_GATES)) {
            let isOn;
            if (color) {
                if (!(color in pendingPalette) && !isPaletteSwitched) {
                    continue;
                }
                // A reset color is the palette's, if any.
                isOn =
                    (color in pendingPalette && !NULL_VALUES.includes(pendingPalette[color])) ||
                    !!this.getWebsiteVariableDefault(color);
            } else if (!(set ? [set] : apart).some((name) => name in this.pendingVariables)) {
                continue;
            } else {
                const value = this.pendingVariables[set];
                isOn = set
                    ? !NULL_VALUES.includes(value) && (!isValueOn || isValueOn(value))
                    : this.getWebsiteVariableValue(apart[0]) !==
                      this.getWebsiteVariableValue(apart[1]);
            }
            if (isOn) {
                gates.add(gate);
            } else {
                gates.delete(gate);
            }
        }
        for (const [gate, isOn] of Object.entries(this.computedGates)) {
            if (isOn) {
                gates.add(gate);
            } else {
                gates.delete(gate);
            }
        }
        htmlEl.setAttribute(THEME_GATES_ATTRIBUTE, [...gates].join(" "));
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
        if (
            "color-palettes-name" in this.pendingVariables ||
            Object.values(this.pendingColors).some((colors) => Object.keys(colors).length)
        ) {
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
        // The options showing these colors (e.g. a preset's text) follow.
        this.trigger("on_dom_updated_handlers");
    }
    /**
     * @returns {Object} what the server computes the colors from: the colors
     *          as currently shown, and which ones are set
     */
    getComputedColorsInputs() {
        const style = getHtmlStyle(this.document);
        const get = (name) => getCSSVariableValue(name, style);
        const pendingPalette = this.getPendingValues(PALETTE_URL);
        const userKeys = new Set(get("o-user-color-keys").replace(/['"]/g, "").split(" "));
        for (const [name, value] of Object.entries(pendingPalette)) {
            if (NULL_VALUES.includes(value)) {
                userKeys.delete(name);
            } else {
                userKeys.add(name);
            }
        }
        const isSet = (name) => userKeys.has(name) || !!this.getWebsiteVariableDefault(name);
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
        for (const area of [
            ...["menu", "header-sales_one", "header-sales_two", "header-sales_three"],
            ...["header-sales_four", "footer", "copyright", "breadcrumb", "portal-card"],
        ]) {
            areas[area] = get(area);
            if (isSet(`${area}-custom`)) {
                colors[`${area}-custom`] = get(`${area}-custom`);
            }
        }
        return {
            colors,
            areas,
            user_keys: [...userKeys].filter(Boolean),
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
    debouncedSCSSVariablesCusto = debounce(async (nullValue) => {
        const variables = this.variablesToCustomize;
        this.variablesToCustomize = {};
        await this.makeSCSSCusto(USER_VALUES_URL, variables, nullValue);
    }, 0);
    async customizeWebsiteColors(
        colors = {},
        { colorType, combinationColor, nullValue, resetCcOnEmpty, reloadBundles = true } = {}
    ) {
        const baseURL = "/website/static/src/scss/options/colors/";
        colorType = colorType ? colorType + "_" : "";
        const url = `${baseURL}user_${colorType}color_palette.scss`;

        const finalColors = {};
        for (const [colorName, color] of Object.entries(colors)) {
            finalColors[colorName] = color;
            if (color) {
                const isColorCombination = /^o_cc[12345]$/.test(color);
                if (isColorCombination) {
                    finalColors[combinationColor] = parseInt(color.substring(4));
                    finalColors[colorName] = "";
                } else if (isCSSVariable(color)) {
                    const customProperty = color.match(/var\(--(.+?)\)/)[1];
                    finalColors[colorName] = this.getWebsiteVariableValue(customProperty);
                } else if (!isCSSColor(color)) {
                    finalColors[colorName] = `'${color}'`;
                }
            } else {
                if (resetCcOnEmpty) {
                    finalColors[combinationColor] = "";
                }
                finalColors[colorName] = "";
            }
        }
        this.colorsToCustomize = Object.assign(this.colorsToCustomize, finalColors);
        await this.debouncedSCSSColorsCusto(url, nullValue);
        if (reloadBundles) {
            await this.reloadBundles();
        }
    }
    debouncedSCSSColorsCusto = debounce(async (url, nullValue) => {
        const colors = this.colorsToCustomize;
        this.colorsToCustomize = {};
        await this.makeSCSSCusto(url, colors, nullValue);
    }, 0);
    async makeSCSSCusto(url, values, defaultValue = "null") {
        Object.keys(values).forEach((key) => {
            values[key] = values[key] || defaultValue;
        });
        await this.services.orm.call("website.assets", "make_scss_customization", [url, values]);
    }
    reloadBundles = debounce(this._reloadBundles.bind(this), 0);
    async _reloadBundles() {
        const bundles = await rpc("/website/theme_customize_bundle_reload");
        const documents = [this.document, this.config.extraPreviewDocument].filter(Boolean);
        const allLinksIframeEls = [];
        const proms = [];
        const createLinksProms = (bundleURLs, insertionEl, document) => {
            const newLinkEls = [];
            for (const url of bundleURLs) {
                const linkEl = document.createElement("link");
                linkEl.setAttribute("type", "text/css");
                linkEl.setAttribute("rel", "stylesheet");
                linkEl.setAttribute("href", `${url}#t=${new Date().getTime()}`); // Ensures that the css will be reloaded.
                newLinkEls.push(linkEl);
                proms.push(
                    new Promise((resolve) => {
                        linkEl.addEventListener("load", resolve);
                        linkEl.addEventListener("error", resolve);
                    })
                );
            }
            for (const el of newLinkEls) {
                insertionEl.insertAdjacentElement("afterend", el);
            }
        };
        for (const document of documents) {
            for (const [bundleName, bundleURLs] of Object.entries(bundles)) {
                const selector = `link[href*="${bundleName}"]`;
                const linksIframeEls = document.querySelectorAll(selector);
                if (linksIframeEls.length) {
                    allLinksIframeEls.push(...linksIframeEls);
                    createLinksProms(
                        bundleURLs,
                        linksIframeEls[linksIframeEls.length - 1],
                        document
                    );
                }
            }
        }
        await Promise.all(proms).then(() => {
            for (const el of allLinksIframeEls) {
                el.remove();
            }
        });
        this.dependencies.edit_interaction.restartInteractions();
    }

    // -------------------------------------------------------------------------
    // customize website action
    // -------------------------------------------------------------------------
    loadConfigKey(actionParam) {
        const promises = [];
        for (const paramName of ["views", "assets"]) {
            if (actionParam[paramName]) {
                promises.push(
                    ...actionParam[paramName].map((record) => {
                        if (record.startsWith("!")) {
                            record = record.substring(1);
                        }
                        if (!(record in this.cache)) {
                            this.cache[record] = this._loadBatchKey(record, paramName === "views");
                        }
                        return this.cache[record];
                    })
                );
            }
        }
        return Promise.all(promises);
    }

    _loadBatchKey(key, isViewData) {
        const pendingRequests = isViewData ? this.pendingViewRequests : this.pendingAssetRequests;
        pendingRequests.add(key);
        return new Promise((resolve) => {
            this.resolves[key] = resolve;
            setTimeout(() => {
                if (pendingRequests.size && !this.isDestroyed) {
                    const keys = [...pendingRequests];
                    pendingRequests.clear();
                    rpc("/website/theme_customize_data_get", {
                        keys,
                        is_view_data: isViewData,
                    }).then((r) => {
                        if (!this.isDestroyed) {
                            for (const key of keys) {
                                this.activeRecords[key] = r.includes(key);
                                this.resolves[key]();
                            }
                        }
                    });
                }
            }, 0);
        });
    }

    getConfigKey(key) {
        if (key.startsWith("!")) {
            return !this.activeRecords[key.substring(1)];
        }
        return this.activeRecords[key];
    }

    withCustomHistory(action) {
        const applyFn = action.apply.bind(action);
        action.apply = async (arg) => {
            const oldValue = action.getValue(arg);
            const { value } = arg;
            const blockedApply = (v) => {
                this.services.ui.block({ delay: 2500 });
                return applyFn({ ...arg, value: v })
                    .then(() => {
                        this.trigger("on_dom_updated_handlers");
                    })
                    .finally(() => this.services.ui.unblock());
            };
            await blockedApply(value);
            this.dependencies.domObserver.stageCustomMutation({
                apply: () => blockedApply(value),
                revert: () => blockedApply(oldValue),
            });
        };
    }

    async loadTemplateKey(key) {
        if (!this.getTemplateKey(key)) {
            // TODO: make a python method that can return several templates at
            // once and batch the ORM call.
            this.activeTemplateViews[key] = await this.services.orm.call(
                "ir.ui.view",
                "render_public_asset",
                [`${key}`, {}],
                { context: this.dependencies.websiteBridge.getWebsiteContextLang() },
            );
        }
        return this.getTemplateKey(key);
    }
    toggleTemplate(action, apply) {
        if (!apply) {
            // Empty the container and restore the original content
            action.editingElement.replaceChildren(this.beforePreviewNodes);
            this.beforePreviewNodes = null;
            return;
        }

        if (!this.beforePreviewNodes) {
            // We are about to apply a template on non-previewed content,
            // save that content's nodes.
            this.beforePreviewNodes = [...action.editingElement.childNodes];
        }

        // Empty the container and add the template content
        const templateFragment = parseHTML(this.document, this.getTemplateKey(action.params.view));
        action.editingElement.replaceChildren(templateFragment.firstElementChild);
    }
    getTemplateKey(key) {
        return this.activeTemplateViews[key];
    }
    populateCache(record, value) {
        if (record.startsWith("!")) {
            record = record.substring(1);
        }
        if (!(record in this.cache)) {
            this.cache[record] = value;
        }
        value.then((resolvedValue) => {
            this.activeRecords[record] = resolvedValue;
        });
    }
    setViewsOnSave(views, to_enable) {
        const initialViewsToEnableOnSave = new Set(this.viewsToEnableOnSave);
        const initialViewsToDisableOnSave = new Set(this.viewsToDisableOnSave);
        for (let view of views) {
            const toEnable = view.startsWith("!") ? !to_enable : to_enable;
            view = view.startsWith("!") ? view.substring(1) : view;
            if (toEnable) {
                this.viewsToEnableOnSave.add(view);
                this.viewsToDisableOnSave.delete(view);
            } else {
                this.viewsToDisableOnSave.add(view);
                this.viewsToEnableOnSave.delete(view);
            }
        }
        return () => {
            // "Undo" callback
            this.viewsToEnableOnSave = initialViewsToEnableOnSave;
            this.viewsToDisableOnSave = initialViewsToDisableOnSave;
        };
    }
    isPluginDestroyed() {
        return this.isDestroyed;
    }
}

export class SwitchThemeAction extends BuilderAction {
    static id = "switchTheme";
    static dependencies = ["savePlugin"];
    setup() {
        this.preview = false;
        this.canTimeout = false;
    }
    async apply() {
        const save = await new Promise((resolve) => {
            this.services.dialog.add(ConfirmationDialog, {
                body: _t(
                    "Changing the theme requires leaving the editor. This will save all your changes. Are you sure you want to proceed? Be aware that changing the theme will reset some layout, color, and style customizations."
                ),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        // TODO not reload in savePlugin.save ?
        await this.dependencies.savePlugin.save(/* not in translation */);
        // TODO doAction in savePlugin.save ?
        this.services.action.doAction("website.theme_install_kanban_action", {});
    }
}

export class AddLanguageAction extends BuilderAction {
    static id = "addLanguage";
    static dependencies = ["savePlugin"];
    setup() {
        this.preview = false;
        this.canTimeout = false;
    }
    async apply() {
        const def = Promise.withResolvers();
        // Retrieve the website id to check by default the website checkbox in
        // the dialog box 'action_view_base_language_install'
        const websiteId = this.services.website.currentWebsite.id;
        const save = await new Promise((resolve) => {
            this.services.dialog.add(ConfirmationDialog, {
                body: _t(
                    "Adding a language requires to leave the editor. This will save all your changes, are you sure you want to proceed?"
                ),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        await this.config.builderSidebar.withHiddenSidebar(() =>
            this.dependencies.savePlugin.save({
                shouldSkipAfterSaveHandlers: async () => {
                    await this.services.action.doAction("base.action_view_base_language_install", {
                        additionalContext: {
                            params: {
                                website_id: websiteId,
                                url_return: "[lang]",
                            },
                        },
                        // The `noReload` in the params of the close callback
                        // are the only way we have to know whether the modal
                        // dialog has been cancelled
                        onClose: (closeParams) => def.resolve(!!closeParams?.noReload),
                    });
                    return await def.promise;
                },
            })
        );
    }
}

export class ToggleBodyBgImageAction extends BuilderAction {
    static id = "toggleBodyBgImage";
    static dependencies = ["builderActions", "domObserver", "customizeWebsite", "media"];
    setup() {
        this.canTimeout = false;
    }
    isApplied() {
        return !!this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image");
    }
    async applyConfigWithLoader(config) {
        this.services.ui.block({ delay: 2500 });
        try {
            await this.setBodyBgConfig(config);
        } finally {
            this.services.ui.unblock();
        }
    }
    async setBodyBgConfig(config) {
        // Store the current body bg selection (image + type).
        const variables = {
            "body-image-type": `'${config.type}'`,
            "body-image": config.image ? `'${config.image}'` : "",
        };
        if (!config.image) {
            // Reset stored variables when removing the image entirely.
            variables["body-image-background-position"] = "";
            variables["body-image-pattern-width"] = "";
            variables["body-image-pattern-height"] = "";
        }
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(variables);
        this.trigger("on_dom_updated_handlers");
    }
    getCurrentConfig() {
        return {
            type:
                this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image-type") ||
                "image",
            image: this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image") || "",
        };
    }
    async applyConfig(oldConfig, newConfig) {
        await this.applyConfigWithLoader(newConfig);
        this.dependencies.domObserver.stageCustomMutation({
            apply: () => this.applyConfigWithLoader(newConfig),
            revert: () => this.applyConfigWithLoader(oldConfig),
        });
    }
    async apply({ editingElement: el } = {}) {
        await this.dependencies.media.openMediaDialog(
            this.getMediaDialogProps({ editingElement: el })
        );
    }
    getMediaDialogProps({ editingElement }) {
        return {
            onlyImages: true,
            node: editingElement,
            save: async (imageEl) => {
                const { type: currentType, image: currentImage } = this.getCurrentConfig();
                const oldConfig = { type: currentType, image: currentImage };
                const newConfig = { type: currentType, image: imageEl.src };
                await this.applyConfig(oldConfig, newConfig);
            },
        };
    }
    async clean() {
        const { type: currentType, image: currentImage } = this.getCurrentConfig();
        const oldConfig = { type: currentType, image: currentImage };
        const newConfig = { type: "image", image: "" };
        await this.applyConfig(oldConfig, newConfig);
    }
}

export class ReplaceBodyBgImageAction extends BuilderAction {
    static id = "replaceBodyBgImage";
    static dependencies = ["builderActions"];
    apply(context) {
        return this.dependencies.builderActions.getAction("toggleBodyBgImage").apply(context);
    }
}

export class RemoveBodyBgImageAction extends BuilderAction {
    static id = "removeBodyBgImage";
    static dependencies = ["builderActions"];
    apply() {
        return this.dependencies.builderActions.getAction("toggleBodyBgImage").clean();
    }
}

export class BodyBgPositionOverlayAction extends BuilderAction {
    static id = "bodyBgPositionOverlay";
    static dependencies = [
        "overlayButtons",
        "domObserver",
        "backgroundPositionOption",
        "customizeWebsite",
    ];
    setup() {
        this.withLoadingEffect = false;
        this.canTimeout = false;
    }
    async apply({ editingElement }) {
        const imageEl = await loadImage(getBgImageURLFromEl(editingElement));
        const clearInlinePosition = () => {
            // Remove inline position used for preview once value is stored in
            // variables.
            editingElement.style.backgroundPosition = "";
        };
        const setBackgroundPosition = async (value) => {
            await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                "body-image-background-position": value,
            });
            clearInlinePosition();
        };
        const bgPosition = await new Promise((resolve) => {
            const removeOverlay = this.services.overlay.add(ImagePositionOverlay, {
                targetEl: editingElement,
                close: (position) => {
                    removeOverlay();
                    resolve(position);
                },
                onDrag: (percentPosition) => {
                    // Live preview via inline style; cleared on apply/discard.
                    editingElement.style.backgroundPosition = `${percentPosition.left}% ${percentPosition.top}%`;
                },
                getDelta: () =>
                    this.dependencies.backgroundPositionOption.getDelta(editingElement, imageEl),
                getPosition: () => getComputedStyle(editingElement).backgroundPosition,
                editable: this.editable,
                scrollToElement: false,
            });
        });
        if (bgPosition) {
            const currentPosition =
                this.dependencies.customizeWebsite.getWebsiteVariableValue(
                    "body-image-background-position"
                ) || "";
            this.dependencies.domObserver.applyCustomMutation({
                apply: () => setBackgroundPosition(bgPosition),
                revert: () => setBackgroundPosition(currentPosition),
            });
        } else {
            clearInlinePosition();
        }
    }
}

export class WebsiteConfigAction extends BuilderAction {
    static id = "websiteConfig";
    static dependencies = ["builderActions", "customizeWebsite"];
    setup() {
        this.reload = {};
        this.preview = false;
    }
    async prepare({ actionParam }) {
        return this.dependencies.customizeWebsite.loadConfigKey(actionParam);
    }
    getPriority({ params }) {
        const records = [...(params.views || []), ...(params.assets || [])];
        return records.length;
    }
    isApplied({ params }) {
        const records = [...(params.views || []), ...(params.assets || [])];
        const configKeysIsApplied = records.every((v) =>
            this.dependencies.customizeWebsite.getConfigKey(v)
        );
        if (params.checkVars || params.checkVars === undefined) {
            return (
                configKeysIsApplied &&
                Object.entries(params.vars || {}).every(
                    ([variable, value]) =>
                        value ===
                        this.dependencies.customizeWebsite.getWebsiteVariableValue(variable)
                )
            );
        }
        return configKeysIsApplied;
    }
    async apply(action) {
        return this._toggleConfig(action, true);
    }
    async clean(action) {
        return this._toggleConfig(action, false);
    }

    async _toggleConfig(action, apply) {
        // step 1: enable and disable records
        const updateViews = this._toggleTheme(action, "views", apply);
        const updateAssets = this._toggleTheme(action, "assets", apply);
        // step 2: customize vars
        const updateVars =
            !apply && action.params.varsOnClean
                ? this.dependencies.customizeWebsite.customizeWebsiteVariables(
                      action.params.varsOnClean,
                      "null",
                      apply
                  )
                : action.params.vars
                ? this.dependencies.customizeWebsite.customizeWebsiteVariables(
                      action.params.vars,
                      "null",
                      !apply
                  )
                : Promise.resolve();
        await Promise.all([updateViews, updateAssets, updateVars]);
        if (this.dependencies.customizeWebsite.isPluginDestroyed()) {
            return true;
        }
    }

    async _toggleTheme(action, paramName, apply) {
        if (!action.params[paramName]) {
            return;
        }
        const isViewData = paramName === "views";
        const toEnable = new Set();
        const toDisable = new Set();
        const prepareRecord = (record, disable) => {
            if (record.startsWith("!")) {
                const recordKey = record.substring(1);
                (disable ? toEnable : toDisable).add(recordKey);
                (disable ? toDisable : toEnable).delete(recordKey);
            } else {
                (disable ? toEnable : toDisable).delete(record);
                (disable ? toDisable : toEnable).add(record);
            }
        };
        const shouldReset = isViewData && !!action.params.resetViewArch;
        const records = action.params[paramName] || [];
        const getAction = this.dependencies.builderActions.getAction;
        if (action.selectableContext) {
            if (!apply) {
                // do nothing, we will do it anyway in the apply call
                return;
            }
            for (const item of action.selectableContext.items) {
                for (const a of item.getActions()) {
                    if (getAction(a.actionId) instanceof WebsiteConfigAction) {
                        for (const record of a.actionParam[paramName] || []) {
                            // disable all
                            prepareRecord(record, true);
                        }
                    } else if (getAction(a.actionId) instanceof CompositeAction) {
                        for (const itemAction of a.actionParam.mainParam) {
                            if (getAction(itemAction.action) instanceof WebsiteConfigAction) {
                                for (const record of itemAction.actionParam[paramName] || []) {
                                    prepareRecord(record, true);
                                }
                            }
                        }
                    }
                }
            }
            for (const record of records) {
                // enable selected one
                prepareRecord(record, false);
            }
        } else {
            for (const record of records) {
                // enable on apply, disable on clear
                prepareRecord(record, !apply);
            }
        }
        return this._customizeThemeData(isViewData, shouldReset, toEnable, toDisable);
    }

    /**
     * Aggregates all sets of records `toEnable` / `toDisable` according to
     * whether you are enabling/disabling view data and whether it should reset
     * the arch, so that a RPC call is only done once per tick and per pair
     * view/reset.
     *
     * @param {boolean} isViewData
     * @param {boolean} shouldReset
     * @param {Set<string>} toEnable
     * @param {Set<string>} toDisable
     * @returns {Promise} deferred function
     */
    async _customizeThemeData(isViewData, shouldReset, toEnable, toDisable) {
        const def = Promise.withResolvers();
        this.dependencies.customizeWebsite.getPendingThemeRequests().push({
            isViewData,
            shouldReset,
            toEnable,
            toDisable,
            def,
        });
        setTimeout(() => {
            let aggregatedToEnable = new Set();
            let aggregatedToDisable = new Set();
            const defs = [];
            for (const req of this.dependencies.customizeWebsite.getPendingThemeRequests()) {
                if (req.isViewData === isViewData && req.shouldReset === shouldReset) {
                    // Synchronize with the last request: if a view was enabled
                    // first and then disabled (or the other way around), the
                    // final state should be disabled (or enabled).
                    aggregatedToEnable = aggregatedToEnable.difference(req.toDisable);
                    aggregatedToDisable = aggregatedToDisable.difference(req.toEnable);
                    // Now aggregate.
                    aggregatedToEnable = aggregatedToEnable.union(req.toEnable);
                    aggregatedToDisable = aggregatedToDisable.union(req.toDisable);
                    defs.push(req.def);
                }
            }
            this.dependencies.customizeWebsite.setPendingThemeRequests(
                this.dependencies.customizeWebsite
                    .getPendingThemeRequests()
                    .filter(
                        (req) => req.isViewData !== isViewData || req.shouldReset !== shouldReset
                    )
            );
            if (!aggregatedToEnable.size && !aggregatedToDisable.size) {
                defs.map((def) => def.resolve());
                return;
            } else {
                rpc("/website/theme_customize_data", {
                    is_view_data: isViewData,
                    enable: [...aggregatedToEnable],
                    disable: [...aggregatedToDisable],
                    reset_view_arch: shouldReset,
                })
                    .then(() => Promise.all(defs.map((def) => def.resolve())))
                    .catch(() => Promise.all(defs.map((def) => def.reject())));
            }
        }, 0);
        return def.promise;
    }
}

export class PreviewableWebsiteConfigAction extends BuilderAction {
    static id = "previewableWebsiteConfig";
    static dependencies = ["customizeWebsite", "domObserver"];
    getPriority({ params }) {
        return (params.previewClass || "")?.trim().split(/\s+/).filter(Boolean).length || 0;
    }
    isApplied({ editingElement: el, params }) {
        if (params.previewClass === undefined || params.previewClass === "") {
            return true;
        }
        return params.previewClass.split(/\s+/).every((cls) => el.classList.contains(cls));
    }
    apply({ editingElement: el, isPreviewing, params }) {
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.add(cls));
        }
        if (!isPreviewing) {
            const viewsToApply = params["views"] || [];
            let undoApplyCallback;
            this.dependencies.domObserver.applyCustomMutation({
                apply: () => {
                    undoApplyCallback = this.dependencies.customizeWebsite.setViewsOnSave(
                        viewsToApply,
                        true
                    );
                },
                revert: () => {
                    undoApplyCallback();
                },
            });
        }
    }
    clean({ editingElement: el, isPreviewing, params }) {
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.remove(cls));
        }
        if (!isPreviewing) {
            const viewsToClean = params["views"] || [];
            let undoCleanCallback;
            this.dependencies.domObserver.applyCustomMutation({
                apply: () => {
                    undoCleanCallback = this.dependencies.customizeWebsite.setViewsOnSave(
                        viewsToClean,
                        false
                    );
                },
                revert: () => {
                    undoCleanCallback();
                },
            });
        }
    }
}

class TemplatePreviewableWebsiteConfigAction extends WebsiteConfigAction {
    static id = "templatePreviewableWebsiteConfig";

    setup() {
        this.reload = {};
        this.preview = true;
    }

    async apply(action) {
        if (!action.isPreviewing) {
            await super.apply(action);
        } else {
            await this.renderPreview(action);
        }
    }

    async clean(action) {
        if (!action.isPreviewing) {
            await super.clean(action);
        }
    }

    async renderPreview({ editingElement: el, params }) {
        if (params.templateId && !el.closest(params.placeExcludeRootClosest)) {
            const renderedEl = renderToElement(params.templateId);
            const targetEl = el;
            if (targetEl) {
                if (params.placeBefore) {
                    for (const el of targetEl.querySelectorAll(params.placeBefore)) {
                        el.insertAdjacentElement("beforebegin", renderedEl.cloneNode(true));
                    }
                }
                if (params.placeAfter) {
                    for (const el of targetEl.querySelectorAll(params.placeAfter)) {
                        el.insertAdjacentElement("afterend", renderedEl.cloneNode(true));
                    }
                }
            }
        }
        // Wait one frame to get the proper fade-in animation effect.
        // The promise ensures this completes before continuing, avoiding a race
        // that could mark the element o_dirty and trigger an unnecessary save.
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.add(cls));
        }
    }
}

export class SelectTemplateAction extends BuilderAction {
    static id = "selectTemplate";
    static dependencies = ["customizeWebsite"];
    async prepare({ actionParam }) {
        return await this.dependencies.customizeWebsite.loadTemplateKey(actionParam.view);
    }
    isApplied({ editingElement, params: { templateClass } }) {
        if (templateClass) {
            return !!editingElement.querySelector(`.${templateClass}`);
        }
        return true;
    }
    async apply(action) {
        return this.dependencies.customizeWebsite.toggleTemplate(action, true);
    }
    clean(action) {
        return this.dependencies.customizeWebsite.toggleTemplate(action, false);
    }
}

export class CustomizeWebsiteVariableAction extends BuilderAction {
    static id = "customizeWebsiteVariable";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    isApplied({ params: { mainParam: variable } = {}, value }) {
        const currentValue = this.dependencies.customizeWebsite.getWebsiteVariableValue(variable);
        return (
            // There might be unquoted values in existing databases.
            currentValue === value || `'${currentValue}'` === value
        );
    }
    getValue({ params: { mainParam: variable } }) {
        const currentValue = this.dependencies.customizeWebsite.getWebsiteVariableValue(variable);
        return currentValue;
    }
    getDefaultValue({ params: { mainParam: variable } }) {
        return this.dependencies.customizeWebsite.getWebsiteVariableDefault(variable);
    }
    async apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            {
                [variable]: value,
            },
            nullValue
        );
    }
}

/**
 * Same as `customizeWebsiteVariable`, but previewed live and only written on
 * save. For the variables the compiled CSS reads through `var()`.
 */
export class PreviewWebsiteVariableAction extends CustomizeWebsiteVariableAction {
    static id = "previewWebsiteVariable";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            { [variable]: value },
            nullValue
        );
    }
}

export class CustomizeWebsiteSubVariablesAction extends CustomizeWebsiteVariableAction {
    static id = "customizeWebsiteSubVariables";
    getValue({ params: { mainParam: variable, subVariablesConfig = {} } }) {
        const subVariables = subVariablesConfig[variable] || [];
        // A global variable returns the common value of its sub-variables
        // if they are all identical. Otherwise, it returns null. And each
        // sub-variable always returns its own current value.
        const currentValue = this._subVariablesValue([variable, ...subVariables]);
        return currentValue;
    }
    async apply({ params, value }) {
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            this.getVariablesToUpdate(params, value),
            params.nullValue
        );
    }
    getVariablesToUpdate({ mainParam: variable, nullValue = "null", subVariablesConfig = {} }, value) {
        // 1. A single variable with potential sub-variables: update all.
        const variablesToUpdate = [variable, ...(subVariablesConfig[variable] || [])].map(
            (name) => [name, value]
        );
        const allSubVariables = Object.values(subVariablesConfig)[0] || [];
        const otherSubVariables = allSubVariables.filter((v) => v !== variable);
        // 2. A sub-variable linked to a global one: update the sub-variable,
        // then update the global variable based on the current values of all
        // sub-variables.
        if (allSubVariables.length === otherSubVariables.length + 1) {
            variablesToUpdate.push([
                Object.keys(subVariablesConfig)[0],
                this._subVariablesValue(otherSubVariables) === value ? value : nullValue,
            ]);
        }
        return Object.fromEntries(variablesToUpdate);
    }
    /**
     * Returns the shared value of a list of CSS variables, or `null`
     * if they differ.
     *
     * @param {string[]} variables
     */
    _subVariablesValue(variables) {
        const values = variables.map(
            this.dependencies.customizeWebsite.getWebsiteVariableValue.bind(this)
        );
        if (new Set(values).size === 1) {
            return values[0];
        }
        return null;
    }
}

export class PreviewWebsiteSubVariablesAction extends CustomizeWebsiteSubVariablesAction {
    static id = "previewWebsiteSubVariables";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params, value }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            this.getVariablesToUpdate(params, value),
            params.nullValue
        );
    }
}

/**
 * Resets website variables: previews their default, writes `null` on save.
 */
export class ResetWebsiteVariablesAction extends BuilderAction {
    static id = "resetWebsiteVariables";
    static dependencies = ["customizeWebsite"];
    apply({ params: { mainParam: variables } }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            Object.fromEntries(variables.map((variable) => [variable, ""]))
        );
    }
}

export class CustomizeWebsiteColorAction extends BuilderAction {
    static id = "customizeWebsiteColor";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    getValue({ params: { mainParam: color, colorType, gradientColor, combinationColor } }) {
        const style = getHtmlStyle(this.document);
        if (gradientColor) {
            const gradientValue =
                this.dependencies.customizeWebsite.getWebsiteVariableValue(gradientColor);
            if (gradientValue) {
                // Pass through style to restore rgb/a which might
                // have been lost during SCSS generation process.
                // TODO Remove this once colorpicker will be able
                // to cope with #rrggbb gradient color elements.
                const el = document.createElement("div");
                el.style.setProperty("background-image", gradientValue);
                return el.style.getPropertyValue("background-image");
            }
        }
        return getCSSVariableValue(color, style);
    }
    async apply({
        params: { mainParam: color, colorType, gradientColor, combinationColor, nullValue },
        value,
    }) {
        if (gradientColor) {
            let colorValue = "";
            let gradientValue = "";
            if (isColorGradient(value)) {
                gradientValue = value;
            } else {
                colorValue = value;
            }
            const isColorCombination = /^o_cc[12345]$/.test(value);
            await this.dependencies.customizeWebsite.customizeWebsiteColors(
                {
                    [color]: colorValue,
                },
                {
                    colorType,
                    combinationColor,
                    nullValue,
                    // Do not touch CC if a gradient is being set
                    resetCcOnEmpty: !gradientValue,
                    // Reload bundle will be handled by setting gradient
                    reloadBundles: false,
                }
            );
            await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                [gradientColor]: isColorCombination ? nullValue : gradientValue || nullValue,
            }); // reloads bundles
        } else {
            await this.dependencies.customizeWebsite.customizeWebsiteColors(
                { [color]: value },
                { colorType, combinationColor, resetCcOnEmpty: true, nullValue }
            );
        }
        setBuilderCSSVariables(getHtmlStyle(this.document));
        await Promise.allSettled(
            this.getResource("on_website_color_updated_handlers").map((handler) => handler([color]))
        );
    }
}

/**
 * Same as `customizeWebsiteColor`, but previewed live and only written on
 * save. For the colors the compiled CSS reads through `var()`.
 */
export class PreviewWebsiteColorAction extends CustomizeWebsiteColorAction {
    static id = "previewWebsiteColor";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    async apply({ params: { mainParam: color, colorType, gradientColor, nullValue }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        // A gradient resets the color.
        const isGradient = !!gradientColor && isColorGradient(value);
        customizeWebsite.previewWebsiteColors(
            { [color]: isGradient ? "" : value },
            { colorType, nullValue }
        );
        if (gradientColor) {
            customizeWebsite.previewWebsiteVariables(
                { [gradientColor]: isGradient ? value : "" },
                nullValue
            );
        }
        await Promise.allSettled(
            this.getResource("on_website_color_updated_handlers").map((handler) => handler([color]))
        );
    }
}

export class CustomizeButtonStyleAction extends BuilderAction {
    static id = "customizeButtonStyle";
    static dependencies = ["customizeWebsite"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    isApplied({ params, value }) {
        return this.getValue({ params }) === value;
    }
    getValue({ params: { mainParam: which } }) {
        const style = getHtmlStyle(this.document);
        const isOutline = getCSSVariableValue(`btn-${which}-outline`, style);
        const isFlat = getCSSVariableValue(`btn-${which}-flat`, style);
        return isFlat === "true" ? "flat" : isOutline === "true" ? "outline" : "fill";
    }
    async apply({ params: { mainParam: which, nullValue }, value }) {
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            {
                [`btn-${which}-outline`]: value === "outline" ? "true" : "false",
                [`btn-${which}-flat`]: value === "flat" ? "true" : "false",
            },
            nullValue
        );
    }
}

export class PreviewButtonStyleAction extends CustomizeButtonStyleAction {
    static id = "previewButtonStyle";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params: { mainParam: which }, value }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables({
            [`btn-${which}-outline`]: value === "outline" ? "true" : "false",
            [`btn-${which}-flat`]: value === "flat" ? "true" : "false",
        });
    }
}

/**
 * Same as `customizeWebsiteColor` for an area (header, footer...: a color
 * preset, a custom color or a gradient), previewed and written on save.
 */
export class PreviewAreaColorAction extends CustomizeWebsiteColorAction {
    static id = "previewAreaColor";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params: { mainParam: color, gradientColor, combinationColor, nullValue }, value }) {
        const preset = value.match(/^o_cc([1-5])$/)?.[1];
        const gradient = isColorGradient(value) ? value : "";
        const colors = { [color]: preset || gradient ? "" : value };
        if (preset || !value) {
            colors[combinationColor] = preset || "";
        }
        this.dependencies.customizeWebsite.previewWebsiteColors(colors, { nullValue });
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            { [gradientColor]: gradient || nullValue },
            nullValue
        );
    }
}

/**
 * The link style (`link-underline`), previewed with Bootstrap's link
 * decorations it gives, which the CSS reads.
 */
export class PreviewLinkStyleAction extends PreviewWebsiteVariableAction {
    static id = "previewLinkStyle";
    apply({ params: { mainParam: variable }, value }) {
        const style = value.replace(/^'(.*)'$/, "$1");
        this.dependencies.customizeWebsite.previewWebsiteVariables({ [variable]: value }, "null", {
            "link-decoration": style === "always" ? "underline" : "none",
            "link-hover-decoration": style === "never" ? "none" : "underline",
        });
    }
}

registry.category("website-plugins").add(CustomizeWebsitePlugin.id, CustomizeWebsitePlugin);
