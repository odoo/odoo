import { getCSSVariableValue, isColorCombinationName } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { isColorGradient, isCSSColor } from "@web/core/utils/colors";

export class CustomizeWebsitePlugin extends Plugin {
    static id = "customizeWebsite";
    static dependencies = ["builderActions", "history", "savePlugin"];
    static shared = ["customizeWebsiteColors", "makeSCSSCusto", "withHistoryFromLoad"];

    resources = {
        builder_actions: this.getActions(),
    };

    cache = {};
    activeRecords = {};
    pendingViewRequests = new Set();
    pendingAssetRequests = new Set();
    resolves = {};
    getActions() {
        return {
            customizeWebsiteVariable: this.withHistoryFromLoad({
                isApplied: ({ param: { mainParam: variable } = {}, value }) => {
                    const currentValue = this.getWebsiteVariableValue(variable);
                    return currentValue === `'${value}'`;
                },
                getValue: ({ param: { mainParam: variable } }) => {
                    const currentValue = this.getWebsiteVariableValue(variable);
                    return currentValue;
                },
                load: async ({ param: { mainParam: variable, nullValue = "null" }, value }) => {
                    await this.customizeWebsiteVariables(
                        {
                            [variable]: value,
                        },
                        nullValue
                    );
                },
            }),
            customizeWebsiteColor: this.withHistoryFromLoad({
                getValue: ({ param: { mainParam: color, colorType, gradientColor } }) => {
                    const style = this.document.defaultView.getComputedStyle(
                        this.document.documentElement
                    );
                    if (gradientColor) {
                        const gradientValue = this.getWebsiteVariableValue(gradientColor);
                        if (gradientValue) {
                            return gradientValue.substring(1, gradientValue.length - 1); // Unquote
                        }
                    }
                    return getCSSVariableValue(color, style);
                },
                load: async ({ param: { mainParam: color, colorType, gradientColor }, value }) => {
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
                            { colorType }
                        );
                        await this.customizeWebsiteVariables({
                            [gradientColor]: gradientValue,
                        }); // reloads bundles
                    } else {
                        await this.customizeWebsiteColors({ [color]: value }, { colorType });
                        await this.reloadBundles();
                    }
                },
            }),
            switchTheme: {
                load: async () => {
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
                load: async () => {
                    // Retrieve the website id to check by default the website checkbox in
                    // the dialog box 'action_view_base_language_install'
                    const websiteId = this.service.website.currentWebsite.id;
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
                    // TODO not reload in savePlugin.save ?
                    await this.dependencies.savePlugin.save(/* not in translation */);
                    // TODO doAction in savePlugin.save ?
                    this.services.action.doAction("base.action_view_base_language_install", {
                        website_id: websiteId,
                        url_return: "[land]",
                    });
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
                    const style = this.document.defaultView.getComputedStyle(
                        this.document.documentElement
                    );
                    return getCSSVariableValue("body-image-type", style);
                },
                load: async ({ editingElement: el, param, value, historyImageSrc }) => {
                    const getAction = this.dependencies.builderActions.getAction;
                    const oldValue = getAction("customizeBodyBgType").getValue({ param });
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
                        await this.customizeWebsiteVariables({
                            "body-image-type": `'${value}'`,
                            "body-image": `'${imageSrc}'`,
                        });
                    }
                    return { imageSrc, oldImageSrc, oldValue };
                },
                apply: ({
                    editingElement,
                    param,
                    value,
                    loadResult: { imageSrc, oldImageSrc, oldValue },
                }) => {
                    if (oldImageSrc) {
                        oldImageSrc = oldImageSrc.substring(1, oldImageSrc.length - 1); // Unquote
                    }
                    if (oldValue !== "NONE") {
                        oldValue = oldValue.substring(1, oldValue.length - 1); // Unquote
                    }
                    const getAction = this.dependencies.builderActions.getAction;
                    this.dependencies.history.addCustomMutation({
                        apply: () => {
                            this.services.ui.block({ delay: 2500 });
                            getAction("customizeBodyBgType")
                                .load({ editingElement, param, value, historyImageSrc: imageSrc })
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
                                    param,
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
                load: async ({ param }) => {
                    // TODO
                    const getAction = this.dependencies.builderActions.getAction;
                    await getAction("customizeWebsiteVariable").load({
                        param: {
                            mainParam: param.variable,
                        },
                    });
                },
            },
            customizeButtonStyle: this.withHistoryFromLoad({
                isApplied: ({ param, value }) => {
                    const getAction = this.dependencies.builderActions.getAction;
                    const currentValue = getAction("customizeButtonStyle").getValue({ param });
                    return currentValue === value;
                },
                getValue: ({ param: { mainParam: which } }) => {
                    const style = this.document.defaultView.getComputedStyle(
                        this.document.documentElement
                    );
                    const isOutline = getCSSVariableValue(`btn-${which}-outline`, style);
                    const isFlat = getCSSVariableValue(`btn-${which}-flat`, style);
                    return isFlat === "true" ? "flat" : isOutline === "true" ? "outline" : "fill";
                },
                load: async ({ param: { mainParam: which, nullValue }, value }) => {
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
                isReload: true,
                prepare: async ({ actionParam }) => this.loadConfigKey(actionParam),
                getPriority: ({ param }) => {
                    const records = [...(param.views || []), ...(param.assets || [])];
                    return records.length;
                },
                isApplied: ({ param }) => {
                    const records = [...(param.views || []), ...(param.assets || [])];
                    return records.every((v) => this.getConfigKey(v));
                },
                apply: (action) => this.toggleConfig(action, true),
                clean: (action) => this.toggleConfig(action, false),
            },
        };
    }
    getWebsiteVariableValue(variable) {
        const style = this.document.defaultView.getComputedStyle(this.document.documentElement);
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
        }
        return finalValue;
    }
    async customizeWebsiteVariables(variables = {}, nullValue) {
        if (!Object.keys(variables).length) {
            return;
        }
        await this.makeSCSSCusto(
            "/website/static/src/scss/options/user_values.scss",
            variables,
            nullValue
        );
        await this.reloadBundles();
    }
    async customizeWebsiteColors(colors = {}, { colorType, nullValue } = {}) {
        const baseURL = "/website/static/src/scss/options/colors/";
        colorType = colorType ? colorType + "_" : "";
        const url = `${baseURL}user_${colorType}color_palette.scss`;

        const finalColors = {};
        for (const [colorName, color] of Object.entries(colors)) {
            finalColors[colorName] = color;
            if (color) {
                if (isColorCombinationName(color)) {
                    finalColors[colorName] = parseInt(color);
                } else if (!isCSSColor(color)) {
                    finalColors[colorName] = `'${color}'`;
                }
            }
        }
        return this.makeSCSSCusto(url, finalColors, nullValue);
    }
    async makeSCSSCusto(url, values, defaultValue = "null") {
        Object.keys(values).forEach((key) => {
            values[key] = values[key] || defaultValue;
        });
        return this.services.orm.call("web_editor.assets", "make_scss_customization", [
            url,
            values,
        ]);
    }
    async reloadBundles() {
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
        const updateVars = action.param.vars
            ? this.customizeWebsiteVariables(action.param.vars)
            : Promise.resolve();

        await Promise.all([updateViews, updateAssets, updateVars]);
        if (this.isDestroyed) {
            return true;
        }
    }

    toggleTheme(action, paramName, apply) {
        if (!action.param[paramName]) {
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
        const shouldReset = isViewData && !!action.param.resetViewArch;
        const records = action.param[paramName] || [];
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
        return rpc("/website/theme_customize_data", {
            is_view_data: isViewData,
            enable: [...toEnable],
            disable: [...toDisable],
            reset_view_arch: shouldReset,
        });
    }

    getConfigKey(key) {
        if (key.startsWith("!")) {
            return !this.activeRecords[key.substring(1)];
        }
        return this.activeRecords[key];
    }
    withHistoryFromLoad(action) {
        const loadFn = action.load;
        const load = async ({ editingElement, param, value }) => {
            const oldValue = action.getValue({ editingElement, param });
            await loadFn({ editingElement, param, value });
            return oldValue;
        };
        const apply = ({ editingElement, param, value, loadResult: oldValue }) => {
            const blockedLoad = (v) => {
                this.services.ui.block({ delay: 2500 });
                loadFn({ editingElement, param, value: v })
                    .then(() => {
                        this.dispatchTo("trigger_dom_updated");
                    })
                    .finally(() => this.services.ui.unblock());
            };
            this.dependencies.history.addCustomMutation({
                apply: () => blockedLoad(value),
                revert: () => blockedLoad(oldValue),
            });
        };
        return { ...action, load, apply };
    }
}

registry.category("website-plugins").add(CustomizeWebsitePlugin.id, CustomizeWebsitePlugin);
