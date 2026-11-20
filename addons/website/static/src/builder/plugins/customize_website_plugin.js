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
 */

/**
 * @typedef {((colors: string[]) => void)[]} on_website_color_updated_handlers
 */

export const NO_IMAGE_SELECTION = Symbol.for("NoImageSelection");

/**
 * @typedef { Object } BodyBackgroundConfig
 * @property { string } type
 * @property { string } image
 *
 * @typedef { Object } ViewsOnSave
 * @property { string[] } enable
 * @property { string[] } disable
 *
 * @typedef {(data: {
 *     actionId: string,
 *     params: import("@html_builder/core/builder_action").ActionParams,
 *     loadResult?: import("@html_builder/core/builder_action").LoadResult,
 *     nodeId?: import("@html_editor/core/dom_reference_map_plugin").NodeId,
 *     before: import("@html_builder/core/builder_action").ActionValue,
 *     after: import("@html_builder/core/builder_action").ActionValue,
 * }) => Promise<void>} website_custom_value
 * @typedef {(data: {
 *     before: BodyBackgroundConfig,
 *     after: BodyBackgroundConfig,
 * }) => Promise<void>} body_background
 * @typedef {(data: {
 *     nodeId: import("@html_editor/core/dom_reference_map_plugin").NodeId,
 *     before: string,
 *     after: string,
 * }) => Promise<void>} body_background_position
 * @typedef {(data: { before: ViewsOnSave, after: ViewsOnSave }) => void} views_on_save
 */

export class CustomizeWebsitePlugin extends Plugin {
    static id = "customizeWebsite";
    static dependencies = [
        "builderActions",
        "savePlugin",
        "edit_interaction",
        "websiteBridge",
        "history",
        "domReferenceMap",
    ];
    static shared = [
        "customizeWebsiteColors",
        "customizeWebsiteVariables",
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
    ];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        history_data_properties: {
            website_custom_value: {
                apply: (data) => this.replayCustomValue(data, data.after),
                revert: (data) => this.replayCustomValue(data, data.before),
            },
            body_background: {
                apply: ({ after }) =>
                    this.dependencies.builderActions
                        .getAction("toggleBodyBgImage")
                        .applyConfigWithLoader(after),
                revert: ({ before }) =>
                    this.dependencies.builderActions
                        .getAction("toggleBodyBgImage")
                        .applyConfigWithLoader(before),
            },
            body_background_position: {
                apply: ({ nodeId, after }) => this.replayBackgroundPosition(nodeId, after),
                revert: ({ nodeId, before }) => this.replayBackgroundPosition(nodeId, before),
            },
            views_on_save: {
                apply: ({ after }) => this.restoreViewsOnSave(after),
                revert: ({ before }) => this.restoreViewsOnSave(before),
            },
        },
        builder_actions: {
            CustomizeWebsiteVariableAction,
            CustomizeWebsiteSubVariablesAction,
            CustomizeWebsiteColorAction,
            SwitchThemeAction,
            AddLanguageAction,
            CustomizeButtonStyleAction,
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
        const { font_urls: fontURLs = [], ...bundles } = await rpc(
            "/website/theme_customize_bundle_reload"
        );
        const documents = [this.document, this.config.extraPreviewDocument].filter(Boolean);
        const allLinksIframeEls = [];
        const proms = [];
        const createLinksProms = (bundleURLs, insertionEl, document, position = "afterend") => {
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
                insertionEl.insertAdjacentElement(position, el);
            }
        };
        for (const document of documents) {
            const fontLinkEls = document.head.querySelectorAll(
                'link[rel="stylesheet"][href^="https://fonts.googleapis.com/css"], ' +
                    'link[rel="stylesheet"][href*="/google-font-"]'
            );
            allLinksIframeEls.push(...fontLinkEls);
            createLinksProms(fontURLs, document.head, document, "beforeend");
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
        action.historyApply = action.apply.bind(action);
        action.apply = async (arg) => {
            const data = {
                actionId: action.constructor.id,
                params: arg.params,
                loadResult: arg.loadResult,
                nodeId:
                    arg.editingElement &&
                    this.dependencies.domReferenceMap.register(arg.editingElement),
                before: action.getValue(arg),
                after: arg.value,
            };
            await this.dependencies.history.apply("website_custom_value", data);
        };
    }

    /**
     * Replay a recorded builder action with its stored context and value.
     *
     * @param {Object} operation
     * @param {string} operation.actionId
     * @param {import("@html_builder/core/builder_action").ActionParams} operation.params
     * @param {import("@html_builder/core/builder_action").LoadResult} [operation.loadResult]
     * @param {import("@html_editor/core/dom_reference_map_plugin").NodeId} [operation.nodeId]
     * @param {import("@html_builder/core/builder_action").ActionValue} value
     * @returns {Promise<void>}
     */
    async replayCustomValue({ actionId, params, loadResult, nodeId }, value) {
        this.services.ui.block({ delay: 2500 });
        try {
            await this.dependencies.builderActions.getAction(actionId).historyApply({
                params,
                loadResult,
                value,
                editingElement: nodeId && this.dependencies.domReferenceMap.getNodeById(nodeId),
            });
            this.trigger("on_dom_updated_handlers");
        } finally {
            this.services.ui.unblock();
        }
    }

    /**
     * Restore the body background position and clear its temporary inline style.
     *
     * @param {import("@html_editor/core/dom_reference_map_plugin").NodeId} nodeId
     * @param {string} value The CSS background-position value.
     * @returns {Promise<void>}
     */
    async replayBackgroundPosition(nodeId, value) {
        await this.customizeWebsiteVariables({ "body-image-background-position": value });
        this.dependencies.domReferenceMap.getNodeById(nodeId).style.backgroundPosition = "";
    }

    async loadTemplateKey(key) {
        if (!this.getTemplateKey(key)) {
            // TODO: make a python method that can return several templates at
            // once and batch the ORM call.
            this.activeTemplateViews[key] = await this.services.orm.call(
                "ir.ui.view",
                "render_public_asset",
                [`${key}`, {}],
                { context: this.dependencies.websiteBridge.getWebsiteContextLang() }
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
        const before = this.getViewsOnSave();
        const viewsToEnable = new Set(before.enable);
        const viewsToDisable = new Set(before.disable);
        for (let view of views) {
            const toEnable = view.startsWith("!") ? !to_enable : to_enable;
            view = view.startsWith("!") ? view.substring(1) : view;
            if (toEnable) {
                viewsToEnable.add(view);
                viewsToDisable.delete(view);
            } else {
                viewsToDisable.add(view);
                viewsToEnable.delete(view);
            }
        }
        const after = { enable: [...viewsToEnable], disable: [...viewsToDisable] };
        this.dependencies.history.apply("views_on_save", { before, after });
    }

    /**
     * Snapshot the view keys queued for activation or deactivation on save.
     *
     * @returns {{enable: string[], disable: string[]}}
     */
    getViewsOnSave() {
        return { enable: [...this.viewsToEnableOnSave], disable: [...this.viewsToDisableOnSave] };
    }

    /**
     * Restore the queued view changes from a history snapshot.
     *
     * @param {{enable: string[], disable: string[]}} state
     * @returns {void}
     */
    restoreViewsOnSave({ enable, disable }) {
        this.viewsToEnableOnSave = new Set(enable);
        this.viewsToDisableOnSave = new Set(disable);
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
    static dependencies = ["builderActions", "customizeWebsite", "media", "history"];
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
        await this.dependencies.history.apply("body_background", {
            before: oldConfig,
            after: newConfig,
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
        "backgroundPositionOption",
        "customizeWebsite",
        "history",
        "domReferenceMap",
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
            await this.dependencies.history.apply("body_background_position", {
                nodeId: this.dependencies.domReferenceMap.register(editingElement),
                before: currentPosition,
                after: bgPosition,
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
    static dependencies = ["customizeWebsite", "history"];
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
            this.dependencies.customizeWebsite.setViewsOnSave(viewsToApply, true);
        }
    }
    clean({ editingElement: el, isPreviewing, params }) {
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.remove(cls));
        }
        if (!isPreviewing) {
            const viewsToClean = params["views"] || [];
            this.dependencies.customizeWebsite.setViewsOnSave(viewsToClean, false);
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
    async apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            {
                [variable]: value,
            },
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
    async apply({
        params: { mainParam: variable, nullValue = "null", subVariablesConfig = {} },
        value,
    }) {
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
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            Object.fromEntries(variablesToUpdate),
            nullValue
        );
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

registry.category("website-plugins").add(CustomizeWebsitePlugin.id, CustomizeWebsitePlugin);
