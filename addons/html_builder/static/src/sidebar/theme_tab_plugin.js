import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { isCSSColor } from "@web/core/utils/colors";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { getCSSVariableValue, isColorCombinationName } from "../utils/utils_css";
import { withSequence } from "@html_editor/utils/resource";

export class ThemeTabPlugin extends Plugin {
    static id = "themeTab";
    static dependencies = ["builderActions", "history", "savePlugin"];
    static shared = ["makeSCSSCusto"];
    resources = {
        builder_actions: this.getActions(),
        theme_options: [
            withSequence(
                10,
                this.getThemeOptionBlock(
                    "theme-colors",
                    _t("Colors"),
                    "html_builder.ThemeColorsOption"
                )
            ),
            withSequence(
                20,
                this.getThemeOptionBlock(
                    "website-settings",
                    _t("Website"),
                    "html_builder.ThemeWebsiteSettingsOption"
                )
            ),
            withSequence(
                30,
                this.getThemeOptionBlock(
                    "theme-paragraph",
                    _t("Paragraph"),
                    "html_builder.ThemeParagraphOption"
                )
            ),
            withSequence(
                40,
                this.getThemeOptionBlock(
                    "theme-headings",
                    _t("Headings"),
                    "html_builder.ThemeHeadingsOption"
                )
            ),
            withSequence(
                50,
                this.getThemeOptionBlock(
                    "theme-button",
                    _t("Button"),
                    "html_builder.ThemeButtonOption"
                )
            ),
            withSequence(
                60,
                this.getThemeOptionBlock("theme-link", _t("Link"), "html_builder.ThemeLinkOption")
            ),
            withSequence(
                70,
                this.getThemeOptionBlock(
                    "theme-input",
                    _t("Input Fields"),
                    "html_builder.ThemeInputOption"
                )
            ),
            withSequence(
                80,
                this.getThemeOptionBlock(
                    "theme-advanced",
                    _t("Advanced"),
                    "html_builder.ThemeAdvancedOption"
                )
            ),
        ],
    };
    setup() {}
    getActions() {
        return {
            customizeWebsiteVariable: {
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
                apply: () => this.stuffHappened(),
            },
            customizeWebsiteColor: {
                getValue: ({ param: { mainParam: color } }) => {
                    const style = this.document.defaultView.getComputedStyle(
                        this.document.documentElement
                    );
                    return getCSSVariableValue(color, style);
                },
                load: async ({ param: { mainParam: color }, value }) => {
                    await this.customizeWebsiteColors({ [color]: value });
                    await this.reloadBundles();
                },
                apply: () => this.stuffHappened(),
            },
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
                    return currentValue === value;
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
                load: async ({ editingElement: el, value }) => {
                    let imageSrc = "";
                    if (value === "NONE") {
                        await this.customizeWebsiteVariables({
                            "body-image-type": "'image'",
                            "body-image": "",
                        });
                    } else {
                        const getAction = this.dependencies.builderActions.getAction;
                        imageSrc = await getAction("replaceBgImage").load({ el });
                        await this.customizeWebsiteVariables({
                            "body-image-type": `'${value}'`,
                            "body-image": `'${imageSrc}'`,
                        });
                    }
                    return imageSrc;
                },
                apply: () => this.stuffHappened(),
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
            customizeButtonStyle: {
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
                apply: () => this.stuffHappened(),
            },
            customizeWebsiteVariableAndAssets: {
                isApplied: ({ param: { variable, assets } }) => {
                    console.log("customizeWebsiteVariableAndAssets.get", variable, assets);
                    return "outline";
                },
                clean: ({ param: { variable, assets } }) => {
                    console.log("customizeWebsiteVariableAndAssets.clean", variable, assets);
                },
                load: async ({ param: { variable, assets }, value }) => {
                    console.log("customizeWebsiteVariableAndAssets.apply", variable, assets, value);
                },
                apply: () => this.stuffHappened(),
            },
        };
    }
    stuffHappened() {
        // TODO Find a way to be inside history... and to get options redrawn.
        this.dispatchTo("step_added_handlers", {
            step: {},
            stepCommonAncestor: this.document.body,
            isPreviewing: false,
        });
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
    getThemeOptionBlock(id, name, template) {
        // TODO Have a specific kind of options container that takes the specific parameters like name, no element, no selector...
        const el = this.document.createElement("div");
        el.dataset.name = name;
        this.document.body.appendChild(el); // Currently editingElement needs to be isConnected

        return {
            id: id,
            element: el,
            hasOverlayOptions: false,
            headerMiddleButton: false,
            isClonable: false,
            isRemovable: false,
            options: [
                {
                    template: template,
                    selector: "*",
                },
            ],
            optionsContainerTopButtons: [],
            snippetModel: {},
        };
    }
}

registry.category("website-plugins").add(ThemeTabPlugin.id, ThemeTabPlugin);
