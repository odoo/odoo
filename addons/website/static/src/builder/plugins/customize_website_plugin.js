/** @odoo-module native */
import { BuilderAction } from "@html_builder/core/builder_action";
import { CompositeAction } from "@html_builder/core/composite_action_plugin";
import { isCSSVariable, setBuilderCSSVariables } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { isColorGradient, isCSSColor } from "@web/core/utils/format/colors";
import { renderToElement } from "@web/core/utils/render";
import { debounce } from "@web/core/utils/timing";
import { ConfirmationDialog } from "@web/ui/dialog";

const log = makeLogger("website.builder.plugin.customize_website");

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

export const NO_IMAGE_SELECTION = Symbol.for("NoImageSelection");

export class CustomizeWebsitePlugin extends Plugin {
    static id = "customizeWebsite";
    static dependencies = [
        "builderActions",
        "history",
        "savePlugin",
        "edit_interaction",
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
        builder_actions: {
            CustomizeWebsiteVariableAction,
            CustomizeWebsiteColorAction,
            SwitchThemeAction,
            AddLanguageAction,
            CustomizeBodyBgTypeAction,
            CustomizeButtonStyleAction,
            WebsiteConfigAction,
            PreviewableWebsiteConfigAction,
            TemplatePreviewableWebsiteConfigAction,
            SelectTemplateAction,
        },
        color_combination_getters: withSequence(5, (el, actionParam) => {
            const combination = actionParam.combinationColor;
            if (combination) {
                const style = getHtmlStyle(this.document);
                return `o_cc${getCSSVariableValue(combination, style)}`;
            }
        }),
        save_handlers: this.onSave.bind(this),
    };

    async onSave() {
        log.logic("onSave", () => ({
            enable: this.viewsToEnableOnSave.size,
            disable: this.viewsToDisableOnSave.size,
        }));
        if (this.viewsToEnableOnSave.size || this.viewsToDisableOnSave.size) {
            const endSaveViews = log.perf("onSave theme_customize_data");
            await rpc("/website/theme_customize_data", {
                is_view_data: true,
                enable: [...this.viewsToEnableOnSave],
                disable: [...this.viewsToDisableOnSave],
                reset_view_arch: false,
            });
            endSaveViews();
            this.viewsToEnableOnSave.clear();
            this.viewsToDisableOnSave.clear();
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
     * @typedef {{ isViewData: boolean, shouldReset: boolean, toEnable: Set<string>, toDisable: Set<string>, def: Deferred, }} pendingThemeRequest
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
        let tempValue = finalValue;
        while (tempValue) {
            finalValue = tempValue;
            tempValue = getCSSVariableValue(tempValue.replaceAll("'", ""), style);
            if (tempValue === finalValue) {
                break;
            }
        }
        if (finalValue.startsWith(`'`)) {
            finalValue = finalValue.substring(1, finalValue.length - 1);
        }
        return finalValue;
    }
    async customizeWebsiteVariables(
        variables = {},
        nullValue = "null",
        clean = false,
        reloadBundles = true,
    ) {
        this.variablesToCustomize = Object.assign(this.variablesToCustomize, variables);
        if (!Object.keys(this.variablesToCustomize).length) {
            log.logic("customizeWebsiteVariables skip: no variables", () => ({
                clean,
                reloadBundles,
            }));
            return;
        }
        if (clean) {
            for (const variable in variables) {
                this.variablesToCustomize[variable] = nullValue;
            }
        }
        log.pipeline("customizeWebsiteVariables", () => ({
            pending: Object.keys(this.variablesToCustomize),
            clean,
            reloadBundles,
        }));
        const endCusto = log.perf("customizeWebsiteVariables scss custo");
        await this.debouncedSCSSVariablesCusto(nullValue);
        endCusto();
        if (reloadBundles) {
            const endReload = log.perf("customizeWebsiteVariables reloadBundles");
            await this.reloadBundles();
            endReload();
        }
    }
    debouncedSCSSVariablesCusto = debounce(async (nullValue) => {
        const variables = this.variablesToCustomize;
        this.variablesToCustomize = {};
        log.pipeline("debouncedSCSSVariablesCusto flush", () => ({
            count: Object.keys(variables).length,
            nullValue,
        }));
        await this.makeSCSSCusto(
            "/website/static/src/scss/options/user_values.scss",
            variables,
            nullValue,
        );
    }, 0);
    async customizeWebsiteColors(
        colors = {},
        {
            colorType,
            combinationColor,
            nullValue,
            resetCcOnEmpty,
            reloadBundles = true,
        } = {},
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
                    finalColors[colorName] =
                        this.getWebsiteVariableValue(customProperty);
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
        const pending = (this.colorsToCustomize[url] ??= { colors: {}, nullValue });
        Object.assign(pending.colors, finalColors);
        pending.nullValue = nullValue;
        log.pipeline("customizeWebsiteColors", () => ({
            url,
            count: Object.keys(finalColors).length,
            pendingCount: Object.keys(pending.colors).length,
            reloadBundles,
        }));
        const endColorsCusto = log.perf("customizeWebsiteColors scss custo");
        await this.debouncedSCSSColorsCusto();
        endColorsCusto();
        if (reloadBundles) {
            const endColorsReload = log.perf("customizeWebsiteColors reloadBundles");
            await this.reloadBundles();
            endColorsReload();
        }
    }
    debouncedSCSSColorsCusto = debounce(async () => {
        const byUrl = this.colorsToCustomize;
        this.colorsToCustomize = {};
        log.pipeline("debouncedSCSSColorsCusto flush", () => ({
            urls: Object.keys(byUrl),
        }));
        for (const [url, { colors, nullValue }] of Object.entries(byUrl)) {
            await this.makeSCSSCusto(url, colors, nullValue);
        }
    }, 0);
    async makeSCSSCusto(url, values, defaultValue = "null") {
        Object.keys(values).forEach((key) => {
            values[key] = values[key] || defaultValue;
        });
        const endUpdateScss = log.perf("makeSCSSCusto update_scss_customization", {
            url,
        });
        await this.services.orm.call("website.assets", "update_scss_customization", [
            url,
            values,
        ]);
        endUpdateScss();
    }
    reloadBundles = debounce(this._reloadBundles.bind(this), 0);

    destroy() {
        super.destroy();
        this.debouncedSCSSVariablesCusto.cancel();
        this.debouncedSCSSColorsCusto.cancel();
        this.reloadBundles.cancel();
        log.lifecycle("destroy: debounced customizations cancelled");
    }

    async _reloadBundles() {
        if (this.isDestroyed) {
            log.logic("_reloadBundles skip: plugin destroyed");
            return;
        }
        const endFetchBundles = log.perf(
            "_reloadBundles theme_customize_bundle_reload",
        );
        const bundles = await rpc("/website/theme_customize_bundle_reload");
        endFetchBundles();
        const allLinksIframeEls = [];
        const proms = [];
        const createLinksProms = (bundleURLs, insertionEl) => {
            const newLinkEls = [];
            for (const url of bundleURLs) {
                const linkEl = this.document.createElement("link");
                linkEl.setAttribute("type", "text/css");
                linkEl.setAttribute("rel", "stylesheet");
                linkEl.setAttribute("href", `${url}#t=${new Date().getTime()}`);
                newLinkEls.push(linkEl);
                proms.push(
                    new Promise((resolve) => {
                        linkEl.addEventListener("load", resolve);
                        linkEl.addEventListener("error", resolve);
                    }),
                );
            }
            for (const el of newLinkEls) {
                insertionEl.insertAdjacentElement("afterend", el);
            }
        };
        for (const [bundleName, bundleURLs] of Object.entries(bundles)) {
            const selector = `link[href*="${bundleName}"]`;
            const linksIframeEls = this.document.querySelectorAll(selector);
            if (linksIframeEls.length) {
                allLinksIframeEls.push(...linksIframeEls);
                createLinksProms(bundleURLs, linksIframeEls[linksIframeEls.length - 1]);
            }
        }
        log.pipeline("_reloadBundles swapping stylesheet links", () => ({
            bundles: Object.keys(bundles).length,
            oldLinks: allLinksIframeEls.length,
            newLinks: proms.length,
        }));
        const endLinksLoad = log.perf("_reloadBundles stylesheet links load", () => ({
            count: proms.length,
        }));
        await Promise.all(proms).then(() => {
            for (const el of allLinksIframeEls) {
                el.remove();
            }
        });
        endLinksLoad();
        if (this.isDestroyed) {
            log.logic("_reloadBundles skip restartInteractions: plugin destroyed");
            return;
        }
        this.dependencies.edit_interaction.restartInteractions();
    }

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
                            log.logic("loadConfigKey cache miss", () => ({
                                record,
                                paramName,
                            }));
                            this.cache[record] = this._loadBatchKey(
                                record,
                                paramName === "views",
                            );
                        }
                        return this.cache[record];
                    }),
                );
            }
        }
        return Promise.all(promises);
    }

    _loadBatchKey(key, isViewData) {
        const pendingRequests = isViewData
            ? this.pendingViewRequests
            : this.pendingAssetRequests;
        pendingRequests.add(key);
        return new Promise((resolve) => {
            this.resolves[key] = resolve;
            setTimeout(() => {
                if (pendingRequests.size && !this.isDestroyed) {
                    const keys = [...pendingRequests];
                    pendingRequests.clear();
                    log.pipeline("_loadBatchKey flush", () => ({
                        count: keys.length,
                        isViewData,
                    }));
                    const endLoadKeys = log.perf(
                        "_loadBatchKey theme_customize_data_get",
                        {
                            count: keys.length,
                            isViewData,
                        },
                    );
                    rpc("/website/theme_customize_data_get", {
                        keys,
                        is_view_data: isViewData,
                    }).then((r) => {
                        endLoadKeys(() => ({
                            active: r?.length,
                            destroyed: this.isDestroyed,
                        }));
                        if (!this.isDestroyed) {
                            for (const key of keys) {
                                this.activeRecords[key] = r.includes(key);
                                this.resolves[key]();
                                delete this.resolves[key];
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
                        this.dispatchTo("trigger_dom_updated");
                    })
                    .finally(() => this.services.ui.unblock());
            };
            log.pipeline("withCustomHistory apply", () => ({
                action: action.constructor.id,
                value,
                oldValue,
            }));
            await blockedApply(value);
            this.dependencies.history.addCustomMutation({
                apply: () => blockedApply(value),
                revert: () => blockedApply(oldValue),
            });
        };
    }

    async loadTemplateKey(key) {
        if (!this.getTemplateKey(key)) {
            const endRenderAsset = log.perf("loadTemplateKey render_public_asset", {
                key,
            });
            this.activeTemplateViews[key] = await this.services.orm.call(
                "ir.ui.view",
                "render_public_asset",
                [`${key}`, {}],
            );
            endRenderAsset();
        }
        return this.getTemplateKey(key);
    }
    toggleTemplate(action, apply) {
        log.logic("toggleTemplate", () => ({
            apply,
            view: action.params.view,
            hasBeforePreviewNodes: !!this.beforePreviewNodes,
        }));
        if (!apply) {
            if (this.beforePreviewNodes) {
                action.editingElement.replaceChildren(...this.beforePreviewNodes);
                this.beforePreviewNodes = null;
            }
            return;
        }

        if (!this.beforePreviewNodes) {
            this.beforePreviewNodes = [...action.editingElement.childNodes];
        }

        const templateFragment = parseHTML(
            this.document,
            this.getTemplateKey(action.params.view),
        );
        action.editingElement.replaceChildren(...templateFragment.childNodes);
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
        log.pipeline("setViewsOnSave", () => ({ views, to_enable }));
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
                    "Changing theme requires to leave the editor. This will save all your changes, are you sure you want to proceed? Be careful that changing the theme will reset all your color customizations.",
                ),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            log.logic("SwitchThemeAction apply: user cancelled");
            return;
        }
        const endSwitchSave = log.perf("SwitchThemeAction apply save");
        await this.dependencies.savePlugin.save();
        endSwitchSave();
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
        const def = new Deferred();
        const websiteId = this.services.website.currentWebsite.id;
        const save = await new Promise((resolve) => {
            this.services.dialog.add(ConfirmationDialog, {
                body: _t(
                    "Adding a language requires to leave the editor. This will save all your changes, are you sure you want to proceed?",
                ),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            log.logic("AddLanguageAction apply: user cancelled", () => ({ websiteId }));
            return;
        }
        const endLanguageSave = log.perf("AddLanguageAction apply save", { websiteId });
        await this.config.builderSidebar.withHiddenSidebar(() =>
            this.dependencies.savePlugin.save({
                shouldSkipAfterSaveHandlers: async () => {
                    await this.services.action.doAction(
                        "base.action_view_base_language_install",
                        {
                            additionalContext: {
                                params: {
                                    website_id: websiteId,
                                    url_return: "[lang]",
                                },
                            },
                            onClose: (closeParams) =>
                                def.resolve(!!closeParams?.noReload),
                        },
                    );
                    return await def;
                },
            }),
        );
        endLanguageSave();
    }
}

export class CustomizeBodyBgTypeAction extends BuilderAction {
    static id = "customizeBodyBgType";
    static dependencies = ["builderActions", "history", "customizeWebsite"];
    isApplied({ value }) {
        const getAction = this.dependencies.builderActions.getAction;
        const currentValue = getAction("customizeBodyBgType").getValue();
        return [`'${value}'`, value].includes(currentValue);
    }
    getValue() {
        const bgImage = getComputedStyle(this.document.querySelector("#wrapwrap"))[
            "background-image"
        ];
        if (bgImage === "none") {
            return "NONE";
        }
        const style = getHtmlStyle(this.document);
        return getCSSVariableValue("body-image-type", style);
    }
    async load({ editingElement: el, params, value, historyImageSrc }) {
        const getAction = this.dependencies.builderActions.getAction;
        const oldValue = getAction("customizeBodyBgType").getValue({ params });
        const oldImageSrc =
            this.dependencies.customizeWebsite.getWebsiteVariableValue("body-image");
        let imageSrc = "";
        log.logic("CustomizeBodyBgTypeAction load", () => ({
            value,
            oldValue,
            fromHistory: !!historyImageSrc,
        }));
        if (value === "NONE") {
            await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                "body-image-type": "'image'",
                "body-image": "",
            });
        } else {
            const imageEl =
                historyImageSrc || (await getAction("replaceBgImage").load({ el }));
            if (imageEl) {
                imageSrc = imageEl.src;
                await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                    "body-image-type": `'${value}'`,
                    "body-image": `'${imageSrc}'`,
                });
            } else {
                log.logic("CustomizeBodyBgTypeAction load: no image selected", () => ({
                    value,
                }));
                imageSrc = NO_IMAGE_SELECTION;
            }
        }
        return { imageSrc, oldImageSrc, oldValue };
    }
    apply({
        editingElement,
        params,
        value,
        loadResult: { imageSrc, oldImageSrc, oldValue },
    }) {
        if (imageSrc === NO_IMAGE_SELECTION) {
            log.logic("CustomizeBodyBgTypeAction apply skip: no image selected");
            return;
        }
        const getAction = this.dependencies.builderActions.getAction;
        this.dependencies.history.addCustomMutation({
            apply: () => {
                this.services.ui.block({ delay: 2500 });
                getAction("customizeBodyBgType")
                    .load({ editingElement, params, value, historyImageSrc: imageSrc })
                    .then(() => {
                        this.dispatchTo("trigger_dom_updated");
                    })
                    .finally(() => this.services.ui.unblock());
            },
            revert: () => {
                this.services.ui.block({ delay: 2500 });
                getAction("customizeBodyBgType")
                    .load({
                        editingElement,
                        params,
                        value: oldValue,
                        historyImageSrc: oldImageSrc,
                    })
                    .then(() => {
                        this.dispatchTo("trigger_dom_updated");
                    })
                    .finally(() => this.services.ui.unblock());
            },
        });
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
        log.pipeline("WebsiteConfigAction prepare", () => ({
            views: actionParam.views?.length || 0,
            assets: actionParam.assets?.length || 0,
        }));
        return this.dependencies.customizeWebsite.loadConfigKey(actionParam);
    }
    getPriority({ params }) {
        const records = [...(params.views || []), ...(params.assets || [])];
        return records.length;
    }
    isApplied({ params }) {
        const records = [...(params.views || []), ...(params.assets || [])];
        const configKeysIsApplied = records.every((v) =>
            this.dependencies.customizeWebsite.getConfigKey(v),
        );
        if (params.checkVars || params.checkVars === undefined) {
            return (
                configKeysIsApplied &&
                Object.entries(params.vars || {}).every(
                    ([variable, value]) =>
                        value ===
                        this.dependencies.customizeWebsite.getWebsiteVariableValue(
                            variable,
                        ),
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
        log.pipeline("WebsiteConfigAction toggleConfig", () => ({
            apply,
            views: action.params.views?.length || 0,
            assets: action.params.assets?.length || 0,
            vars: Object.keys(action.params.vars || {}).length,
            varsOnClean: Object.keys(action.params.varsOnClean || {}).length,
        }));
        const updateViews = this._toggleTheme(action, "views", apply);
        const updateAssets = this._toggleTheme(action, "assets", apply);
        const updateVars =
            !apply && action.params.varsOnClean
                ? this.dependencies.customizeWebsite.customizeWebsiteVariables(
                      action.params.varsOnClean,
                      "null",
                      apply,
                  )
                : action.params.vars
                  ? this.dependencies.customizeWebsite.customizeWebsiteVariables(
                        action.params.vars,
                        "null",
                        !apply,
                    )
                  : Promise.resolve();
        const endToggleConfig = log.perf("WebsiteConfigAction toggleConfig", { apply });
        await Promise.all([updateViews, updateAssets, updateVars]);
        endToggleConfig();
        if (this.dependencies.customizeWebsite.isPluginDestroyed()) {
            log.logic("WebsiteConfigAction toggleConfig: plugin destroyed", { apply });
            return true;
        }
    }

    async _toggleTheme(action, paramName, apply) {
        if (!action.params[paramName]) {
            log.logic("WebsiteConfigAction toggleTheme skip: no records", () => ({
                paramName,
                apply,
            }));
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
                log.logic(
                    "WebsiteConfigAction toggleTheme skip: selectable clean",
                    () => ({
                        paramName,
                    }),
                );
                return;
            }
            for (const item of action.selectableContext.items) {
                for (const a of item.getActions()) {
                    if (getAction(a.actionId) instanceof WebsiteConfigAction) {
                        for (const record of a.actionParam[paramName] || []) {
                            prepareRecord(record, true);
                        }
                    } else if (getAction(a.actionId) instanceof CompositeAction) {
                        for (const itemAction of a.actionParam.mainParam) {
                            if (
                                getAction(itemAction.action) instanceof
                                WebsiteConfigAction
                            ) {
                                for (const record of itemAction.actionParam[
                                    paramName
                                ] || []) {
                                    prepareRecord(record, true);
                                }
                            }
                        }
                    }
                }
            }
            for (const record of records) {
                prepareRecord(record, false);
            }
        } else {
            for (const record of records) {
                prepareRecord(record, !apply);
            }
        }
        log.pipeline("WebsiteConfigAction toggleTheme", () => ({
            paramName,
            apply,
            selectable: !!action.selectableContext,
            shouldReset,
            toEnable: [...toEnable],
            toDisable: [...toDisable],
        }));
        return this._customizeThemeData(isViewData, shouldReset, toEnable, toDisable);
    }

    /**
     * @param {boolean} isViewData
     * @param {boolean} shouldReset
     * @param {Set<string>} toEnable
     * @param {Set<string>} toDisable
     * @returns {Promise}
     */
    async _customizeThemeData(isViewData, shouldReset, toEnable, toDisable) {
        const def = new Deferred();
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
                    aggregatedToEnable = aggregatedToEnable.difference(req.toDisable);
                    aggregatedToDisable = aggregatedToDisable.difference(req.toEnable);
                    aggregatedToEnable = aggregatedToEnable.union(req.toEnable);
                    aggregatedToDisable = aggregatedToDisable.union(req.toDisable);
                    defs.push(req.def);
                }
            }
            this.dependencies.customizeWebsite.setPendingThemeRequests(
                this.dependencies.customizeWebsite
                    .getPendingThemeRequests()
                    .filter(
                        (req) =>
                            req.isViewData !== isViewData ||
                            req.shouldReset !== shouldReset,
                    ),
            );
            log.pipeline("WebsiteConfigAction flush theme requests", () => ({
                requests: defs.length,
                isViewData,
                shouldReset,
                enable: aggregatedToEnable.size,
                disable: aggregatedToDisable.size,
            }));
            if (!aggregatedToEnable.size && !aggregatedToDisable.size) {
                log.logic("WebsiteConfigAction flush: nothing to toggle", () => ({
                    requests: defs.length,
                }));
                defs.map((def) => def.resolve());
                return;
            } else {
                const endThemeData = log.perf(
                    "WebsiteConfigAction theme_customize_data",
                    () => ({
                        isViewData,
                        requests: defs.length,
                    }),
                );
                rpc("/website/theme_customize_data", {
                    is_view_data: isViewData,
                    enable: [...aggregatedToEnable],
                    disable: [...aggregatedToDisable],
                    reset_view_arch: shouldReset,
                })
                    .then(() => {
                        endThemeData();
                        return Promise.all(defs.map((def) => def.resolve()));
                    })
                    .catch(() => Promise.all(defs.map((def) => def.reject())));
            }
        }, 0);
        return def;
    }
}

export class PreviewableWebsiteConfigAction extends BuilderAction {
    static id = "previewableWebsiteConfig";
    static dependencies = ["customizeWebsite", "history"];
    setup() {
        this.dispatchResize = () => this.window.dispatchEvent(new Event("resize"));
    }
    getPriority({ params }) {
        return (
            (params.previewClass || "")?.trim().split(/\s+/).filter(Boolean).length || 0
        );
    }
    isApplied({ editingElement: el, params }) {
        if (params.previewClass === undefined || params.previewClass === "") {
            return true;
        }
        return params.previewClass
            .split(/\s+/)
            .every((cls) => el.classList.contains(cls));
    }
    apply({ editingElement: el, isPreviewing, params }) {
        log.logic("PreviewableWebsiteConfigAction apply", () => ({
            isPreviewing,
            previewClass: params.previewClass,
            views: params.views?.length || 0,
        }));
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.add(cls));
        }
        this.dependencies.history.applyCustomMutation({
            apply: this.dispatchResize,
            revert: this.dispatchResize,
        });
        if (!isPreviewing) {
            const viewsToApply = params["views"] || [];
            let undoApplyCallback;
            this.dependencies.history.applyCustomMutation({
                apply: () => {
                    undoApplyCallback =
                        this.dependencies.customizeWebsite.setViewsOnSave(
                            viewsToApply,
                            true,
                        );
                },
                revert: () => {
                    undoApplyCallback();
                },
            });
        }
    }
    clean({ editingElement: el, isPreviewing, params }) {
        log.logic("PreviewableWebsiteConfigAction clean", () => ({
            isPreviewing,
            previewClass: params.previewClass,
            views: params.views?.length || 0,
        }));
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.remove(cls));
        }
        this.dependencies.history.applyCustomMutation({
            apply: this.dispatchResize,
            revert: this.dispatchResize,
        });
        if (!isPreviewing) {
            const viewsToClean = params["views"] || [];
            let undoCleanCallback;
            this.dependencies.history.applyCustomMutation({
                apply: () => {
                    undoCleanCallback =
                        this.dependencies.customizeWebsite.setViewsOnSave(
                            viewsToClean,
                            false,
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
        log.logic("TemplatePreviewableWebsiteConfigAction apply", () => ({
            isPreviewing: action.isPreviewing,
            templateId: action.params.templateId,
        }));
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
            log.pipeline(
                "TemplatePreviewableWebsiteConfigAction renderPreview",
                () => ({
                    templateId: params.templateId,
                    placeBefore: params.placeBefore,
                    placeAfter: params.placeAfter,
                }),
            );
            const renderedEl = renderToElement(params.templateId);
            const targetEl = el;
            if (targetEl) {
                if (params.placeBefore) {
                    for (const el of targetEl.querySelectorAll(params.placeBefore)) {
                        el.insertAdjacentElement(
                            "beforebegin",
                            renderedEl.cloneNode(true),
                        );
                    }
                }
                if (params.placeAfter) {
                    for (const el of targetEl.querySelectorAll(params.placeAfter)) {
                        el.insertAdjacentElement(
                            "afterend",
                            renderedEl.cloneNode(true),
                        );
                    }
                }
            }
        }
        if (params.previewClass) {
            params.previewClass.split(/\s+/).forEach((cls) => el.classList.add(cls));
        }
    }
}

export class SelectTemplateAction extends BuilderAction {
    static id = "selectTemplate";
    static dependencies = ["customizeWebsite"];
    async prepare({ actionParam }) {
        log.pipeline("SelectTemplateAction prepare", () => ({
            view: actionParam.view,
        }));
        return await this.dependencies.customizeWebsite.loadTemplateKey(
            actionParam.view,
        );
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
        const currentValue =
            this.dependencies.customizeWebsite.getWebsiteVariableValue(variable);
        return currentValue === value || `'${currentValue}'` === value;
    }
    getValue({ params: { mainParam: variable } }) {
        const currentValue =
            this.dependencies.customizeWebsite.getWebsiteVariableValue(variable);
        return currentValue;
    }
    async apply({ params: { mainParam: variable, nullValue = "null" }, value }) {
        log.pipeline("CustomizeWebsiteVariableAction apply", () => ({
            variable,
            value,
        }));
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            {
                [variable]: value,
            },
            nullValue,
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
    getValue({
        params: { mainParam: color, colorType, gradientColor, combinationColor },
    }) {
        const style = getHtmlStyle(this.document);
        if (gradientColor) {
            const gradientValue =
                this.dependencies.customizeWebsite.getWebsiteVariableValue(
                    gradientColor,
                );
            if (gradientValue) {
                const el = document.createElement("div");
                el.style.setProperty("background-image", gradientValue);
                return el.style.getPropertyValue("background-image");
            }
        }
        return getCSSVariableValue(color, style);
    }
    async apply({
        params: {
            mainParam: color,
            colorType,
            gradientColor,
            combinationColor,
            nullValue,
        },
        value,
    }) {
        log.logic("CustomizeWebsiteColorAction apply", () => ({
            color,
            colorType,
            gradientColor,
            value,
        }));
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
                    resetCcOnEmpty: !gradientValue,
                    reloadBundles: false,
                },
            );
            await this.dependencies.customizeWebsite.customizeWebsiteVariables({
                [gradientColor]: isColorCombination
                    ? nullValue
                    : gradientValue || nullValue,
            });
        } else {
            await this.dependencies.customizeWebsite.customizeWebsiteColors(
                { [color]: value },
                { colorType, combinationColor, resetCcOnEmpty: true, nullValue },
            );
        }
        setBuilderCSSVariables(getHtmlStyle(this.document));
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
        log.pipeline("CustomizeButtonStyleAction apply", () => ({ which, value }));
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(
            {
                [`btn-${which}-outline`]: value === "outline" ? "true" : "false",
                [`btn-${which}-flat`]: value === "flat" ? "true" : "false",
            },
            nullValue,
        );
    }
}

registry
    .category("website-plugins")
    .add(CustomizeWebsitePlugin.id, CustomizeWebsitePlugin);
