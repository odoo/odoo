import { getCSSVariableValue, isCSSVariable } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { isColorGradient, isCSSColor } from "@web/core/utils/colors";
import { Deferred } from "@web/core/utils/concurrency";
import { debounce } from "@web/core/utils/timing";
import { withSequence } from "@html_editor/utils/resource";

export const NO_IMAGE_SELECTION = Symbol.for("NoImageSelection");

export class CustomizeWebsitePlugin extends Plugin {
    static id = "customizeWebsite";
    static dependencies = ["builderActions", "history", "savePlugin"];
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
    ];

    resources = {
        builder_actions: this.getActions(),
        color_combination_getters: withSequence(5, (el, actionParam) => {
            const combination = actionParam.combinationColor;
            if (combination) {
                const style = this.window.getComputedStyle(this.document.documentElement);
                return `o_cc${getCSSVariableValue(combination, style)}`;
            }
        }),
    };

    cache = {};
    activeRecords = {};
    activeTemplateViews = {};
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
    getActions() {
        return {
            customizeWebsiteVariable: this.withCustomHistory({
                isApplied: ({ params: { mainParam: variable } = {}, value }) => {
                    const currentValue = this.getWebsiteVariableValue(variable);
                    return currentValue === value;
                },
                getValue: ({ params: { mainParam: variable } }) => {
                    const currentValue = this.getWebsiteVariableValue(variable);
                    return currentValue;
                },
                apply: async ({ params: { mainParam: variable, nullValue = "null" }, value }) => {
                    await this.customizeWebsiteVariables(
                        {
                            [variable]: value,
                        },
                        nullValue
                    );
                },
            }),
            customizeWebsiteColor: this.withCustomHistory({
                getValue: ({
                    params: { mainParam: color, colorType, gradientColor, combinationColor },
                }) => {
                    const style = this.window.getComputedStyle(this.document.documentElement);
                    if (gradientColor) {
                        const gradientValue = this.getWebsiteVariableValue(gradientColor);
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
                },
                apply: async ({
                    params: {
                        mainParam: color,
                        colorType,
                        gradientColor,
                        combinationColor,
                        nullValue,
                    },
                    value,
                }) => {
                    if (gradientColor) {
                        let colorValue = "";
                        let gradientValue = "";
                        if (isColorGradient(value)) {
                            gradientValue = value;
                        } else {
                            colorValue = value;
                        }
                        await this.customizeWebsiteColors(
                            {
                                [color]: colorValue,
                            },
                            { colorType, combinationColor, nullValue }
                        );
                        await this.customizeWebsiteVariables({
                            [gradientColor]: gradientValue || nullValue,
                        }); // reloads bundles
                    } else {
                        await this.customizeWebsiteColors(
                            { [color]: value },
                            { colorType, combinationColor, nullValue }
                        );
                    }
                },
            }),
            switchTheme: {
                preview: false,
                apply: async () => {
                    const save = await new Promise((resolve) => {
                        this.services.dialog.add(ConfirmationDialog, {
                            body: _t(
                                "Changing theme requires to leave the editor. This will save all your changes, are you sure you want to proceed? Be careful that changing the theme will reset all your color customizations."
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
                },
            },
            addLanguage: {
                preview: false,
                apply: async () => {
                    const def = new Deferred();
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
                    this.config.builderSidebar.toggle(false);
                    await this.dependencies.savePlugin.save(/* not in translation */);
                    await this.services.action.doAction("base.action_view_base_language_install", {
                        additionalContext: {
                            params: {
                                website_id: websiteId,
                                url_return: "[lang]",
                            },
                        },
                        onClose: def.resolve,
                    });
                    await def;
                    this.config.builderSidebar.toggle(true);
                },
            },
            customizeBodyBgType: {
                isApplied: ({ value }) => {
                    const getAction = this.dependencies.builderActions.getAction;
                    const currentValue = getAction("customizeBodyBgType").getValue();
                    // NONE has no extra quote, other values have
                    return [`'${value}'`, value].includes(currentValue);
                },
                getValue: () => {
                    const bgImage = getComputedStyle(this.document.querySelector("#wrapwrap"))[
                        "background-image"
                    ];
                    if (bgImage === "none") {
                        return "NONE";
                    }
                    const style = this.window.getComputedStyle(this.document.documentElement);
                    return getCSSVariableValue("body-image-type", style);
                },
                load: async ({ editingElement: el, params, value, historyImageSrc }) => {
                    const getAction = this.dependencies.builderActions.getAction;
                    const oldValue = getAction("customizeBodyBgType").getValue({ params });
                    const oldImageSrc = this.getWebsiteVariableValue("body-image");
                    let imageSrc = "";
                    if (value === "NONE") {
                        await this.customizeWebsiteVariables({
                            "body-image-type": "'image'",
                            "body-image": "",
                        });
                    } else {
                        imageSrc =
                            historyImageSrc || (await getAction("replaceBgImage").load({ el }));
                        if (imageSrc) {
                            await this.customizeWebsiteVariables({
                                "body-image-type": `'${value}'`,
                                "body-image": `'${imageSrc}'`,
                            });
                        } else {
                            imageSrc = NO_IMAGE_SELECTION;
                        }
                    }
                    return { imageSrc, oldImageSrc, oldValue };
                },
                apply: ({
                    editingElement,
                    params,
                    value,
                    loadResult: { imageSrc, oldImageSrc, oldValue },
                }) => {
                    if (imageSrc === NO_IMAGE_SELECTION) {
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
                },
            },
            removeFont: {
                preview: false,
                apply: async ({ params }) => {
                    // TODO
                    const getAction = this.dependencies.builderActions.getAction;
                    await getAction("customizeWebsiteVariable").load({
                        params: {
                            mainParam: params.variable,
                        },
                    });
                },
            },
            customizeButtonStyle: this.withCustomHistory({
                preview: false,
                isApplied: ({ params, value }) => {
                    const getAction = this.dependencies.builderActions.getAction;
                    const currentValue = getAction("customizeButtonStyle").getValue({ params });
                    return currentValue === value;
                },
                getValue: ({ params: { mainParam: which } }) => {
                    const style = this.window.getComputedStyle(this.document.documentElement);
                    const isOutline = getCSSVariableValue(`btn-${which}-outline`, style);
                    const isFlat = getCSSVariableValue(`btn-${which}-flat`, style);
                    return isFlat === "true" ? "flat" : isOutline === "true" ? "outline" : "fill";
                },
                apply: async ({ params: { mainParam: which, nullValue }, value }) => {
                    await this.customizeWebsiteVariables(
                        {
                            [`btn-${which}-outline`]: value === "outline" ? "true" : "false",
                            [`btn-${which}-flat`]: value === "flat" ? "true" : "false",
                        },
                        nullValue
                    );
                },
            }),
            websiteConfig: {
                reload: {},
                prepare: async ({ actionParam }) => this.loadConfigKey(actionParam),
                getPriority: ({ params }) => {
                    const records = [...(params.views || []), ...(params.assets || [])];
                    return records.length;
                },
                isApplied: ({ params }) => {
                    const records = [...(params.views || []), ...(params.assets || [])];
                    const configKeysIsApplied = records.every((v) => this.getConfigKey(v));
                    if (params.checkVars || params.checkVars === undefined) {
                        return (
                            configKeysIsApplied &&
                            Object.entries(params.vars || {}).every(
                                ([variable, value]) =>
                                    value === this.getWebsiteVariableValue(variable)
                            )
                        );
                    }
                    return configKeysIsApplied;
                },
                apply: async (action) => this.toggleConfig(action, true),
                clean: (action) => this.toggleConfig(action, false),
            },
            selectTemplate: {
                prepare: async ({ actionParam }) => {
                    await this.loadTemplateKey(actionParam.view);
                },
                isApplied: ({ editingElement, params: { templateClass } }) => {
                    if (templateClass) {
                        return !!editingElement.querySelector(`.${templateClass}`);
                    }
                    return true;
                },
                apply: async (action) => this.toggleTemplate(action, true),
                clean: (action) => this.toggleTemplate(action, false),
            },
        };
    }
    getWebsiteVariableValue(variable) {
        const style = this.window.getComputedStyle(this.document.documentElement);
        let finalValue = getCSSVariableValue(variable, style);
        /* TODO dedicated action ?
        if (!params.colorNames) {
            return finalValue;
        }
        */
        let tempValue = finalValue;
        while (tempValue) {
            finalValue = tempValue;
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
    async customizeWebsiteVariables(variables = {}, nullValue = "null", clean = false) {
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
        await this.reloadBundles();
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
    async customizeWebsiteColors(colors = {}, { colorType, combinationColor, nullValue } = {}) {
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
                    delete finalColors[colorName];
                } else if (isCSSVariable(color)) {
                    const customProperty = color.match(/var\(--(.+?)\)/)[1];
                    finalColors[colorName] = this.getWebsiteVariableValue(customProperty);
                } else if (!isCSSColor(color)) {
                    finalColors[colorName] = `'${color}'`;
                }
            }
        }
        this.colorsToCustomize = Object.assign(this.colorsToCustomize, finalColors);
        await this.debouncedSCSSColorsCusto(url, nullValue);
        await this.reloadBundles();
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
        await this.services.orm.call("web_editor.assets", "make_scss_customization", [url, values]);
    }
    reloadBundles = debounce(this._reloadBundles.bind(this), 0);
    async _reloadBundles() {
        const bundles = await rpc("/website/theme_customize_bundle_reload");
        const allLinksIframeEls = [];
        const proms = [];
        const createLinksProms = (bundleURLs, insertionEl) => {
            const newLinkEls = [];
            for (const url of bundleURLs) {
                const linkEl = this.document.createElement("link");
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
        for (const [bundleName, bundleURLs] of Object.entries(bundles)) {
            const selector = `link[href*="${bundleName}"]`;
            const linksIframeEls = this.document.querySelectorAll(selector);
            if (linksIframeEls.length) {
                allLinksIframeEls.push(...linksIframeEls);
                createLinksProms(bundleURLs, linksIframeEls[linksIframeEls.length - 1]);
            }
        }
        await Promise.all(proms).then(() => {
            for (const el of allLinksIframeEls) {
                el.remove();
            }
        });
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

    async toggleConfig(action, apply) {
        // step 1: enable and disable records
        const updateViews = this.toggleTheme(action, "views", apply);
        const updateAssets = this.toggleTheme(action, "assets", apply);
        // step 2: customize vars
        const updateVars =
            !apply && action.params.varsOnClean
                ? this.customizeWebsiteVariables(action.params.varsOnClean, "null", apply)
                : action.params.vars
                ? this.customizeWebsiteVariables(action.params.vars, "null", !apply)
                : Promise.resolve();
        await Promise.all([updateViews, updateAssets, updateVars]);
        if (this.isDestroyed) {
            return true;
        }
    }

    async toggleTheme(action, paramName, apply) {
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
        if (action.selectableContext) {
            if (!apply) {
                // do nothing, we will do it anyway in the apply call
                return;
            }
            for (const item of action.selectableContext.items) {
                for (const a of item.getActions()) {
                    if (a.actionId === "websiteConfig") {
                        for (const record of a.actionParam[paramName] || []) {
                            // disable all
                            prepareRecord(record, true);
                        }
                    } else if (a.actionId === "composite" || a.actionId === "reloadComposite") {
                        for (const itemAction of a.actionParam.mainParam) {
                            if (itemAction.action === "websiteConfig") {
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
        return this.customizeThemeData(isViewData, shouldReset, toEnable, toDisable);
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
    async customizeThemeData(isViewData, shouldReset, toEnable, toDisable) {
        const def = new Deferred();
        this.pendingThemeRequests.push({ isViewData, shouldReset, toEnable, toDisable, def });
        setTimeout(() => {
            let aggregatedToEnable = new Set();
            let aggregatedToDisable = new Set();
            const defs = [];
            for (const req of this.pendingThemeRequests) {
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
            this.pendingThemeRequests = this.pendingThemeRequests.filter(
                (req) => req.isViewData !== isViewData || req.shouldReset !== shouldReset
            );
            if (!aggregatedToEnable.size && !aggregatedToDisable.size) {
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
        return def;
    }

    getConfigKey(key) {
        if (key.startsWith("!")) {
            return !this.activeRecords[key.substring(1)];
        }
        return this.activeRecords[key];
    }
    withCustomHistory(action) {
        const applyFn = action.apply;
        const apply = async (arg) => {
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
            await blockedApply(value);
            this.dependencies.history.addCustomMutation({
                apply: () => blockedApply(value),
                revert: () => blockedApply(oldValue),
            });
        };
        return { preview: false, ...action, apply };
    }

    async loadTemplateKey(key) {
        if (!this.getTemplateKey(key)) {
            // TODO: make a python method that can return several templates at
            // once and batch the ORM call.
            this.activeTemplateViews[key] = await this.services.orm.call(
                "ir.ui.view",
                "render_public_asset",
                [`${key}`, {}]
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
}

registry.category("website-plugins").add(CustomizeWebsitePlugin.id, CustomizeWebsitePlugin);
