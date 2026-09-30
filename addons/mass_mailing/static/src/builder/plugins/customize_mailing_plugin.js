import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { CUSTOMIZE_MAILING_VARIABLES } from "@mass_mailing/builder/plugins/customize_mailing_variables";
import { CUSTOMIZE_MAILING_VARIABLES_DEFAULTS } from "./customize_mailing_variables";
import { splitSelectorAroundCommasOutsideParentheses } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { getCSSVariableValue } from "@html_editor/utils/formatting";

const RE_SELECTOR_ENDS_WITH_GT_STAR = />\s*\*\s*$/;
export const PRIORITY_STYLES = {
    h1: new Set(["font-family"]),
    h2: new Set(["font-family"]),
    h3: new Set(["font-family"]),
    p: new Set(["font-family"]),
    hr: new Set(["border-top-width", "border-top-style", "border-top-color"]),
};

export class CustomizeMailingPlugin extends Plugin {
    static id = "mass_mailing.CustomizeMailingPlugin";
    static dependencies = [];
    static shared = ["getVariableValue", "setVariable"];

    resources = {
        builder_actions: {
            CustomizeMailingVariable,
        },
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
        snippet_preview_dialog_stylesheets_handlers: ({ iframe }) => {
            const styleSheet = this.extractStylesheetForPreview(iframe.contentDocument);
            iframe.contentDocument.adoptedStyleSheets.push(styleSheet);
        },
    };
    getRule = memoize((selector) => this._getRule(selector));

    setup() {
        this.iframeWindow = this.document.defaultView;
        // To have priority over some rules from style assets, the `cssPrefix` is intentionally made
        // very specific (3 depth level).
        this.cssPrefix = ".o_layout .o_mail_wrapper .o_mail_wrapper_td";
        this.styleSheet = new this.iframeWindow.CSSStyleSheet();
        const styleEl = this.editable.querySelector("#design-element");
        if (styleEl) {
            this.parseDesignElement(styleEl);
            styleEl.remove();
        }
        this.setupMailingVariables();
        this.document.adoptedStyleSheets = [...this.document.adoptedStyleSheets, this.styleSheet];
    }

    cleanForSave(clone) {
        const layoutEl = clone.querySelector(".o_layout");
        if (!layoutEl) {
            return;
        }
        const styleEl = this.document.createElement("STYLE");
        styleEl.id = "design-element";
        const cssTextArray = [];
        for (const rule of Array.from(this.styleSheet.cssRules)) {
            if (!rule.style.length) {
                continue;
            }
            cssTextArray.push(rule.cssText);
        }
        styleEl.textContent = cssTextArray.join("\n");
        layoutEl.prepend(styleEl);
    }

    extractStylesheetForPreview(contentDocument) {
        const cssRules = this.styleSheet.cssRules;
        const newStyleSheet = new contentDocument.defaultView.CSSStyleSheet();
        for (const cssRule of cssRules) {
            let previewRule = cssRule.cssText.replace(this.cssPrefix, ".o_add_snippets_preview");
            if (previewRule.includes("> [data-snippet]")) {
                previewRule = previewRule.replace(
                    "> [data-snippet]",
                    ".o_snippet_preview_wrap [data-snippet]"
                );
            }
            newStyleSheet.insertRule(previewRule);
        }
        return newStyleSheet;
    }

    setupMailingVariables() {
        const varRule = this.getRule(this.cssPrefix);
        for (const variable of Object.keys(CUSTOMIZE_MAILING_VARIABLES)) {
            const currentValue = this.getVariableValue(variable);
            const defaultValue =
                Object.values(CUSTOMIZE_MAILING_VARIABLES_DEFAULTS[variable] ?? {})[0] ?? "";
            if (currentValue === "" && defaultValue !== "") {
                varRule.style.setProperty(variable, defaultValue);
            }
            this.refreshMailingVariableSelector(variable);
        }
    }

    refreshMailingVariableSelector(variable) {
        const options = CUSTOMIZE_MAILING_VARIABLES[variable];
        const currentValue = this.getVariableValue(variable);
        let value = "";
        if (currentValue !== "") {
            value = `var(${variable})`;
        }
        for (const selector of options.selectors) {
            const rule = this.getRule(selector);
            for (const property of options.properties) {
                const important = PRIORITY_STYLES[selector]?.has(property) ? "important" : "";
                rule.style.setProperty(property, value, important);
            }
        }
    }

    parseDesignElement(styleEl) {
        const rules = [...styleEl.sheet.cssRules];
        for (const rule of rules) {
            for (const selector of splitSelectorAroundCommasOutsideParentheses(rule.selectorText)) {
                for (const property of rule.style) {
                    const selectors =
                        property !== "font-family"
                            ? [selector]
                            : this.transformFontFamilySelector(selector);
                    for (const selector of selectors) {
                        this.addCSSRule(selector, rule.style, property);
                    }
                }
            }
        }
    }

    addSelectorPrefix(selector) {
        if (!selector.trim().startsWith(this.cssPrefix)) {
            return `${this.cssPrefix} ${selector}`;
        }
        return selector;
    }

    _getRule(selector) {
        selector = this.addSelectorPrefix(selector);
        for (const rule of this.styleSheet.cssRules) {
            if (rule.selectorText === selector) {
                return rule;
            }
        }
        return this.styleSheet.cssRules.item(this.styleSheet.insertRule(`${selector} { }`));
    }

    getVariableValue(variable) {
        return this.getRule(this.cssPrefix).style.getPropertyValue(variable);
    }

    setVariable(variable, value) {
        const currentValue = this.getVariableValue(variable);
        this.getRule(this.cssPrefix).style.setProperty(variable, value);
        if (Boolean(currentValue) !== Boolean(value)) {
            this.refreshMailingVariableSelector(variable);
        }
    }

    /**
     * Ensure that FontAwesome icons are not impacted by font-family selectors
     */
    transformFontFamilySelector(selector) {
        if (selector.trim().endsWith(":not(.fa)")) {
            return [selector];
        }
        if (!selector.endsWith("*")) {
            return [`${selector.trim()}:not(.fa)`, `${selector.trim()} :not(.fa)`];
        } else if (RE_SELECTOR_ENDS_WITH_GT_STAR.test(selector)) {
            return [`${selector.replace(RE_SELECTOR_ENDS_WITH_GT_STAR, "").trim()} :not(.fa)`];
        }
    }

    /**
     * @param {String} selector
     * @param {CSSStyleDeclaration} ruleStyle
     * @param {String} property
     */
    addCSSRule(selector, ruleStyle, property) {
        selector = selector.trim();
        const rule = this.getRule(selector);
        rule.style.setProperty(
            property,
            ruleStyle.getPropertyValue(property),
            ruleStyle.getPropertyPriority(property)
        );
    }
}

export class CustomizeMailingVariable extends BuilderAction {
    static id = "mass_mailing.CustomizeMailingVariable";
    static dependencies = [
        "builderActions",
        "color",
        "mass_mailing.CustomizeMailingPlugin",
        "history",
    ];
    isApplied({ value }) {
        return this.getValue(...arguments) === value;
    }
    /**
     * @param { Object } params
     * @param { String[] } params.selectors
     * @param { string } params.property
     */
    getValue({ params }) {
        const variable = this.dependencies["mass_mailing.CustomizeMailingPlugin"].getVariableValue(
            params.variable
        );
        if (!params.variable.includes("color") || !/var\(/g.test(variable)) {
            return variable;
        }
        const match = variable.match(/var\(--([\w-]+)\)/)[1];
        return getCSSVariableValue(
            match,
            this.window.getComputedStyle(this.document.documentElement)
        );
    }
    apply({ params, value }) {
        const oldValue = this.getValue(...arguments);
        this.dependencies.history.applyCustomMutation({
            apply: () => {
                this.dependencies["mass_mailing.CustomizeMailingPlugin"].setVariable(
                    params.variable,
                    value
                );
            },
            revert: () => {
                this.dependencies["mass_mailing.CustomizeMailingPlugin"].setVariable(
                    params.variable,
                    oldValue
                );
            },
        });
    }
    clean({ params }) {
        const oldValue = this.getValue(...arguments);
        this.dependencies.history.applyCustomMutation({
            apply: () => {
                this.dependencies["mass_mailing.CustomizeMailingPlugin"].setVariable(
                    params.variable,
                    params.clean ?? ""
                );
            },
            revert: () => {
                this.dependencies["mass_mailing.CustomizeMailingPlugin"].setVariable(
                    params.variable,
                    oldValue
                );
            },
        });
    }
}

registry.category("mass_mailing-plugins").add(CustomizeMailingPlugin.id, CustomizeMailingPlugin);
