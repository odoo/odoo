import {
    isCSSVariable,
    setBuilderCSSVariables,
    getBgImageURLFromEl,
} from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { loadBundle } from "@web/core/assets";
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
 * @property { CustomizeWebsitePlugin['previewSavedValues'] } previewSavedValues
 * @property { CustomizeWebsitePlugin['previewBodyImage'] } previewBodyImage
 * @property { CustomizeWebsitePlugin['previewColorVariable'] } previewColorVariable
 * @property { CustomizeWebsitePlugin['getPendingValue'] } getPendingValue
 * @property { CustomizeWebsitePlugin['copyPreviewTo'] } copyPreviewTo
 * @property { CustomizeWebsitePlugin['getColorsCustomization'] } getColorsCustomization
 * @property { CustomizeWebsitePlugin['loadTemplateKey'] } loadTemplateKey
 * @property { CustomizeWebsitePlugin['makeSCSSCusto'] } makeSCSSCusto
 * @property { CustomizeWebsitePlugin['toggleTemplate'] } toggleTemplate
 * @property { CustomizeWebsitePlugin['withCustomHistory'] } withCustomHistory
 * @property { CustomizeWebsitePlugin['populateCache'] } populateCache
 * @property { CustomizeWebsitePlugin['loadConfigKey'] } loadConfigKey
 * @property { CustomizeWebsitePlugin['getConfigKey'] } getConfigKey
 * @property { CustomizeWebsitePlugin['getWebsiteVariableValue'] } getWebsiteVariableValue
 * @property { CustomizeWebsitePlugin['getPendingThemeRequests'] } getPendingThemeRequests
 * @property { CustomizeWebsitePlugin['setPendingThemeRequests'] } setPendingThemeRequests
 * @property { CustomizeWebsitePlugin['isPluginDestroyed'] } isPluginDestroyed
 * @property { CustomizeWebsitePlugin['reloadBundles'] } reloadBundles
 * @property { CustomizeWebsitePlugin['setViewsOnSave'] } setViewsOnSave
 * @property { CustomizeWebsitePlugin['setVariableAssets'] } setVariableAssets
 */

/**
 * @typedef {((colors: string[]) => void)[]} on_website_color_updated_handlers
 */

export const NO_IMAGE_SELECTION = Symbol.for("NoImageSelection");
const USER_VALUES_URL = "/website/static/src/scss/options/user_values.scss";

export class CustomizeWebsitePlugin extends Plugin {
    static id = "customizeWebsite";
    static dependencies = ["builderActions", "domObserver", "savePlugin", "edit_interaction", "websiteBridge"];
    static shared = [
        "customizeWebsiteColors",
        "customizeWebsiteVariables",
        "previewWebsiteVariables",
        "previewSavedValues",
        "previewBodyImage",
        "previewColorVariable",
        "getPendingValue",
        "copyPreviewTo",
        "getColorsCustomization",
        "loadTemplateKey",
        "makeSCSSCusto",
        "toggleTemplate",
        "withCustomHistory",
        "populateCache",
        "loadConfigKey",
        "getConfigKey",
        "getWebsiteVariableValue",
        "getPendingThemeRequests",
        "setPendingThemeRequests",
        "isPluginDestroyed",
        "reloadBundles",
        "setViewsOnSave",
        "setVariableAssets",
    ];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            CustomizeWebsiteVariableAction,
            PreviewWebsiteVariableAction,
            PreviewWebsiteFontSizeAction,
            ResetWebsiteVariablesAction,
            CustomizeWebsiteSubVariablesAction,
            PreviewWebsiteSubVariablesAction,
            CustomizeWebsiteColorAction,
            SwitchThemeAction,
            AddLanguageAction,
            WebsiteConfigAction,
            PreviewableWebsiteConfigAction,
            TemplatePreviewableWebsiteConfigAction,
            SelectTemplateAction,
            ToggleBodyBgImageAction,
            PreviewBodyImageAction,
            PreviewIconFontAction,
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
        const assetsToToggle = { enable: [], disable: [] };
        for (const [variable, assets] of Object.entries(this.variableAssets)) {
            const value = this.getPendingValue(variable);
            if (value !== undefined) {
                assetsToToggle[value === "true" ? "enable" : "disable"].push(...assets);
            }
        }
        if (assetsToToggle.enable.length || assetsToToggle.disable.length) {
            await rpc("/website/theme_customize_data", {
                is_view_data: false,
                ...assetsToToggle,
                reset_view_arch: false,
            });
        }
        // No bundle reload: the iframe is reloaded after save. The user values
        // go first: a palette switch there resets the color files.
        const customizations = Object.entries(this.pendingCustomizations).sort(
            ([url1], [url2]) => (url2 === USER_VALUES_URL) - (url1 === USER_VALUES_URL)
        );
        for (const [url, values] of customizations) {
            if (Object.keys(values).length) {
                await this.makeSCSSCusto(url, values);
            }
        }
        this.pendingCustomizations = {};
    }
    cache = {};
    activeRecords = {};
    activeTemplateViews = {};
    viewsToEnableOnSave = new Set();
    viewsToDisableOnSave = new Set();
    /** @type {Object<string, string[]>} assets toggled on save by a variable */
    variableAssets = {};
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
    /** @type {Object<string, Object<string, string>>} values to write, by file URL */
    pendingCustomizations = {};
    /** Preview steps not committed to the history yet. */
    pendingPreviewSteps = [];
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
        let finalValue = getCSSVariableValue(variable, style);
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
     * Previews website variables inline on the iframe root, under two names:
     * - `--<name>` overrides the printed value, which `getWebsiteVariableValue`
     *   and CSS already reading it through `var()` use;
     * - `--o-preview-<name>` is read by the rules that otherwise use the
     *   compiled value (`var(--o-preview-<name>, <compiled value>)`). It only
     *   exists while editing, so the saved site renders exactly the compiled
     *   CSS. It holds the same value, unless `cssValues` gives the CSS one
     *   (e.g. a font family for a font name). `cssValues` can also set
     *   aliases for values derived from the variables, which are not saved.
     * The SCSS customization is only written on save, in the file at `url`.
     *
     * A reset (empty value or `nullValue`) previews the default printed as
     * `--o-default-<name>`, if any, else the last saved value. Another null
     * value than `"null"` saves an explicit value: it previews no value.
     *
     * @param {Object<string, string>} variables
     * @param {string} [nullValue="null"]
     * @param {Object<string, string>} [cssValues]
     * @param {string} [url]
     */
    previewWebsiteVariables(variables, nullValue = "null", cssValues = {}, url = USER_VALUES_URL) {
        const style = this.document.documentElement.style;
        const pending = this.pendingCustomizations[url] || {};
        const isSet = (value) => value && value !== nullValue;
        const htmlStyle = getHtmlStyle(this.document);
        const getDefault = (name) =>
            nullValue === "null" ? getCSSVariableValue(`o-default-${name}`, htmlStyle) : "initial";
        const aliasNames = new Set([...Object.keys(variables), ...Object.keys(cssValues)]);
        const previousState = {
            url,
            variables: Object.keys(variables).map((name) => [
                name,
                pending[name],
                style.getPropertyValue(`--${name}`),
            ]),
            aliases: [...aliasNames].map((name) => [
                name,
                style.getPropertyValue(`--o-preview-${name}`),
            ]),
        };
        const nextState = {
            url,
            variables: Object.entries(variables).map(([name, value]) =>
                isSet(value) ? [name, value, value] : [name, nullValue, getDefault(name)]
            ),
            aliases: [...aliasNames].map((name) => [
                name,
                cssValues[name] ?? (isSet(variables[name]) ? variables[name] : getDefault(name)),
            ]),
        };
        // The root is outside the observed editable: the step goes to the
        // history as commit data, which reverts hover previews and undo.
        this.setPreviewState(nextState);
        this.pendingPreviewSteps.push({ previous: previousState, next: nextState });
    }
    /**
     * Previews values that are not written on save, e.g. the ones a server-side
     * reset gives: they replace any pending value of the same name. Like a
     * preview, it is a history step.
     *
     * @param {Object<string, Object<string, string>>} valuesByUrl the values of
     *        each file (empty: the compiled one)
     */
    previewSavedValues(valuesByUrl) {
        const style = this.document.documentElement.style;
        for (const [url, values] of Object.entries(valuesByUrl)) {
            const pending = this.pendingCustomizations[url] || {};
            const names = Object.keys(values);
            const step = {
                previous: {
                    url,
                    variables: names.map((name) => [
                        name,
                        pending[name],
                        style.getPropertyValue(`--${name}`),
                    ]),
                    aliases: [],
                },
                next: {
                    url,
                    variables: names.map((name) => [name, undefined, values[name]]),
                    aliases: [],
                },
            };
            this.setPreviewState(step.next);
            this.pendingPreviewSteps.push(step);
        }
    }
    /**
     * Previews a color saved in the colors file (e.g. a border color).
     *
     * @param {string} name
     * @param {string} value a CSS color
     */
    previewColorVariable(name, value) {
        const { url, finalColors } = this.getColorsCustomization({ [name]: value }, {});
        this.previewWebsiteVariables(finalColors, "null", { [name]: value }, url);
    }
    /**
     * Previews body image values. The background (`body-image-bg-style()` in
     * `website.scss`) is compiled from all of them: it is previewed as a whole,
     * from these values and the current other ones (see `theme_preview.scss`).
     *
     * @param {Object<string, string>} variables
     * @param {string} [nullValue="null"]
     */
    previewBodyImage(variables, nullValue = "null") {
        const get = (name) => {
            const value = name in variables ? variables[name] : this.getWebsiteVariableValue(name);
            return value && value !== nullValue ? value.replace(/^'(.*)'$/, "$1") : "";
        };
        const image = get("body-image");
        const width = get("body-image-pattern-width");
        const height = get("body-image-pattern-height");
        const isPattern = get("body-image-type") === "pattern";
        this.previewWebsiteVariables(variables, nullValue, {
            "body-image-bg": image ? `url("${image}")` : "none",
            "body-image-size": isPattern
                ? [width || "auto", height].filter(Boolean).join(" ")
                : "cover",
            "body-image-repeat": isPattern ? "repeat" : "no-repeat",
            "body-image-position": get("body-image-background-position") || "center",
        });
    }
    setPreviewState({ url, variables, aliases }) {
        const pending = (this.pendingCustomizations[url] ??= {});
        for (const [name, pendingValue, inlineValue] of variables) {
            if (pendingValue === undefined) {
                delete pending[name];
            } else {
                pending[name] = pendingValue;
            }
            this.setRootProperty(`--${name}`, inlineValue);
        }
        for (const [name, value] of aliases) {
            this.setRootProperty(`--o-preview-${name}`, value);
        }
        // After the aliases: a variable change can change the colors computed
        // from it.
        this.updateBuilderColors();
    }
    /**
     * Updates the website colors that the builder shows (e.g. the color
     * pickers, the color presets' cards) with the previewed ones, when set
     * (see `computeColorSystemPreview`, where the preset buttons' names
     * differ).
     */
    updateBuilderColors() {
        const style = getHtmlStyle(this.document);
        const getPreviewName = (name) =>
            name.replace(
                /-btn-(primary|secondary)(-text)?$/,
                (_, type, isText) => `-btn-${type}-${isText ? "color" : "bg"}`
            );
        setBuilderCSSVariables({
            getPropertyValue: (property) =>
                style.getPropertyValue(`--o-preview-${getPreviewName(property.slice(2))}`) ||
                style.getPropertyValue(property),
        });
    }
    setRootProperty(property, value) {
        // Also on the theme colors preview dialog, if open.
        for (const previewDocument of [this.document, this.config.extraPreviewDocument].filter(
            Boolean
        )) {
            if (value) {
                previewDocument.documentElement.style.setProperty(property, value);
            } else {
                previewDocument.documentElement.style.removeProperty(property);
            }
        }
    }
    /**
     * @param {string} name
     * @param {string} [url]
     * @returns {string|undefined} the value to save on save, if any
     */
    getPendingValue(name, url = USER_VALUES_URL) {
        return this.pendingCustomizations[url]?.[name];
    }
    /**
     * Copies the previewed values to another document showing the website
     * (e.g. the theme colors preview dialog, opened after they were set).
     *
     * @param {Document} previewDocument
     */
    copyPreviewTo(previewDocument) {
        const style = this.document.documentElement.style;
        for (const property of style) {
            if (property.startsWith("--")) {
                previewDocument.documentElement.style.setProperty(
                    property,
                    style.getPropertyValue(property)
                );
            }
        }
    }
    debouncedSCSSVariablesCusto = debounce(async (nullValue) => {
        const variables = this.variablesToCustomize;
        this.variablesToCustomize = {};
        await this.makeSCSSCusto(
            "/website/static/src/scss/options/user_values.scss",
            variables,
            nullValue
        );
    }, 0);
    async customizeWebsiteColors(
        colors = {},
        { colorType, combinationColor, nullValue, resetCcOnEmpty, reloadBundles = true } = {}
    ) {
        const { url, finalColors } = this.getColorsCustomization(colors, {
            colorType,
            combinationColor,
            resetCcOnEmpty,
        });
        this.colorsToCustomize = Object.assign(this.colorsToCustomize, finalColors);
        await this.debouncedSCSSColorsCusto(url, nullValue);
        if (reloadBundles) {
            await this.reloadBundles();
        }
    }
    getColorsCustomization(colors, { colorType, combinationColor, resetCcOnEmpty }) {
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
        return { url, finalColors };
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
        const swapLinks = (bundleURLs, oldLinkEls, document) => {
            const newLinkEls = bundleURLs.map((url) => {
                const linkEl = document.createElement("link");
                linkEl.setAttribute("type", "text/css");
                linkEl.setAttribute("rel", "stylesheet");
                linkEl.setAttribute("href", `${url}#t=${new Date().getTime()}`); // Ensures that the css will be reloaded.
                return linkEl;
            });
            oldLinkEls.at(-1).after(...newLinkEls);
            return Promise.all(
                newLinkEls.map(
                    (linkEl) =>
                        new Promise((resolve) => {
                            linkEl.addEventListener("load", resolve);
                            linkEl.addEventListener("error", resolve);
                        })
                )
            ).then(() => oldLinkEls.forEach((el) => el.remove()));
        };
        const swapBundle = (bundleName) =>
            Promise.all(
                documents.map((document) => {
                    const oldLinkEls = [
                        ...document.querySelectorAll(`link[href*="${bundleName}"]`),
                    ];
                    const bundleURLs = bundles?.[bundleName];
                    return (
                        oldLinkEls.length &&
                        bundleURLs &&
                        swapLinks(bundleURLs, oldLinkEls, document)
                    );
                })
            );
        await swapBundle("web.assets_frontend");
        // The preview rules (see `loadThemePreviewBundle`) are only used while
        // previewing: compiled after the page's, and not waited for.
        swapBundle("website.assets_theme_preview");
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
    /**
     * Enables `assets` on save if `variable` is then saved as `'true'`, or
     * disables them if it is saved as something else.
     *
     * @param {string} variable
     * @param {string[]} assets
     */
    setVariableAssets(variable, assets) {
        this.variableAssets[variable] = assets;
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
    static dependencies = ["builderActions", "customizeWebsite", "media"];
    setup() {
        this.canTimeout = false;
    }
    isApplied() {
        return !!this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image");
    }
    previewConfig(config) {
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
        // An explicit null, so that the removal is previewed.
        this.dependencies.customizeWebsite.previewBodyImage(variables, "NULL");
    }
    getCurrentConfig() {
        return {
            type:
                this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image-type") ||
                "image",
            image: this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image") || "",
        };
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
                this.previewConfig({ type: this.getCurrentConfig().type, image: imageEl.src });
            },
        };
    }
    clean() {
        this.previewConfig({ type: "image", image: "" });
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
    static dependencies = ["overlayButtons", "backgroundPositionOption", "customizeWebsite"];
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
        const setBackgroundPosition = (value) => {
            this.dependencies.customizeWebsite.previewBodyImage({
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
            setBackgroundPosition(bgPosition);
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
        return getCSSVariableValue(`o-default-${variable}`, getHtmlStyle(this.document));
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
 * save. For variables the compiled CSS reads through `var()`, or with
 * `cssValues` (see `previewWebsiteVariables`). `assets` are toggled on save
 * (see `setVariableAssets`).
 */
export class PreviewWebsiteVariableAction extends CustomizeWebsiteVariableAction {
    static id = "previewWebsiteVariable";
    // Drop the parent's `preview = false` and blocking `withCustomHistory`.
    setup() {}
    apply({ params: { mainParam: variable, nullValue = "null", cssValues, assets }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        customizeWebsite.previewWebsiteVariables({ [variable]: value }, nullValue, cssValues);
        if (assets) {
            customizeWebsite.setVariableAssets(variable, assets);
        }
    }
}

/**
 * The other body image values (see `previewBodyImage`).
 */
export class PreviewBodyImageAction extends PreviewWebsiteVariableAction {
    static id = "previewBodyImage";
    apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        this.dependencies.customizeWebsite.previewBodyImage({ [variable]: value }, nullValue);
    }
}

const ICON_FONT_BUNDLES = {
    "Material Symbols Rounded": "web.material_symbols_rounded",
    "Material Symbols Sharp": "web.material_symbols_sharp",
};

/**
 * Previews the icon font: the page only has the font face of its own.
 */
export class PreviewIconFontAction extends PreviewWebsiteVariableAction {
    static id = "previewIconFont";
    async load({ value }) {
        const bundle = ICON_FONT_BUNDLES[value] || "web.material_symbols_outlined";
        await loadBundle(bundle, { targetDoc: this.document });
    }
    apply({ params: { mainParam: variable }, value }) {
        // The icons read `--icon-font-family`, set on the body over the
        // printed one (see `theme_preview.scss`). An empty value is Outlined.
        this.dependencies.customizeWebsite.previewWebsiteVariables({ [variable]: value }, "null", {
            [variable]: `"${value || "Material Symbols Outlined"}"`,
        });
    }
}

/**
 * Resets website variables to their theme default, through
 * `previewWebsiteVariables` (which previews the default).
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

/**
 * `previewWebsiteVariable` for the base and small font sizes: the compiled
 * small font size is their ratio (in em), computed here.
 */
export class PreviewWebsiteFontSizeAction extends PreviewWebsiteVariableAction {
    static id = "previewWebsiteFontSize";
    apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        const customizeWebsite = this.dependencies.customizeWebsite;
        const style = getHtmlStyle(this.document);
        const getSize = (name, printedName) => {
            const size = name === variable ? value : customizeWebsite.getPendingValue(name);
            if (size && size !== nullValue) {
                return parseFloat(size);
            }
            // A reset previews the default.
            return parseFloat(
                getCSSVariableValue(size === undefined ? printedName : `o-default-${name}`, style)
            );
        };
        const ratio =
            getSize("small-font-size", "o-small-font-size") /
            getSize("font-size-base", "font-size-base");
        customizeWebsite.previewWebsiteVariables({ [variable]: value }, nullValue, {
            "small-font-ratio": `${ratio}`,
        });
    }
}

/**
 * Previews a variable and the sub-variables it sets (e.g. a border width and
 * its sides).
 */
export class PreviewWebsiteSubVariablesAction extends PreviewWebsiteVariableAction {
    static id = "previewWebsiteSubVariables";
    getValue({ params: { mainParam: variable, subVariablesConfig = {} } }) {
        const subVariables = subVariablesConfig[variable] || [];
        // A global variable returns the common value of its sub-variables
        // if they are all identical. Otherwise, it returns null. And each
        // sub-variable always returns its own current value.
        return this._subVariablesValue([variable, ...subVariables]);
    }
    apply({ params, value }) {
        this.dependencies.customizeWebsite.previewWebsiteVariables(
            this.getVariablesToUpdate(params, value),
            params.nullValue
        );
    }
    getVariablesToUpdate(
        { mainParam: variable, nullValue = "null", subVariablesConfig = {} },
        value
    ) {
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
// Alias, kept for compatibility with custom modules and themes.
class CustomizeWebsiteSubVariablesAction extends PreviewWebsiteSubVariablesAction {
    static id = "customizeWebsiteSubVariables";
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

registry.category("website-plugins").add(CustomizeWebsitePlugin.id, CustomizeWebsitePlugin);
