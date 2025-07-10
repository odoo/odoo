import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { CUSTOMIZE_MAILING_VARIABLES } from "@mass_mailing_egg/builder/plugins/customize_mailing_variables";

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
    static shared = [
        "addCSSRule",
        "convertObjectToRuleStyle",
        "getRule",
        "getVariableValue",
        "setVariable",
        "transformFontFamilySelector",
    ];

    resources = {
        builder_actions: {
            CustomizeMailingVariable,
        },
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };
    getRule = memoize((selector) => this._getRule(selector));

    setup() {
        this.iframeWindow = this.document.defaultView;
        this.cssPrefix = ".o_mail_wrapper";
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

    convertObjectToRuleStyle(styleObject) {
        const ruleStyle = Object.keys(styleObject);
        const prefixRegex = /^(.+?)(?:\s*!important)?;?$/;
        const priorityRegex = /\s*!important(?=;?$)/;
        Object.assign(ruleStyle, {
            styleObject,
            getPropertyValue: (styleName) =>
                (styleObject[styleName] ?? "").match(prefixRegex)?.[1].trim() ?? "",
            getPropertyPriority: (styleName) =>
                (styleObject[styleName] ?? "").match(priorityRegex)?.[1] ? "important" : "",
        });
        return ruleStyle;
    }

    setupMailingVariables() {
        const varRule = this.getRule(this.cssPrefix);
        for (const [variable, options] of Object.entries(CUSTOMIZE_MAILING_VARIABLES)) {
            const currentValue = this.getVariableValue(variable);
            const defaultValue = options.default ?? "";
            if (currentValue === "" && defaultValue !== "") {
                varRule.style.setProperty(variable, defaultValue);
            }
            for (const selector of options.selectors) {
                const rule = this.getRule(selector);
                for (const property of options.properties) {
                    const important = PRIORITY_STYLES[selector]?.has(property) ? "important" : "";
                    rule.style.setProperty(property, `var(${variable})`, important);
                }
            }
        }
    }

    parseDesignElement(styleEl) {
        const rules = [...styleEl.sheet.cssRules];
        for (const rule of rules) {
            for (const selector of rule.selectorText.split(",")) {
                for (const style of rule.style) {
                    let selectors = [selector];
                    if (style === "font-family") {
                        // TODO EGGMAIL: maybe a better way to protect FontAwesome.
                        // Ensure font-family gets passed to all descendants and never
                        // overwrite font awesome.
                        selectors = this.transformFontFamilySelector(selector);
                    }
                    for (const selector of selectors) {
                        this.addCSSRule({ selector, ruleStyle: rule.style, whitelist: [style] });
                    }
                }
            }
        }
    }

    _getRule(selector) {
        if (!selector.trim().startsWith(this.cssPrefix)) {
            selector = `${this.cssPrefix} ${selector}`;
        }
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
        return this.getRule(this.cssPrefix).style.setProperty(variable, value);
    }

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

    // TODO EGGMAIL: currently receives a CSSStyleDeclaration as ruleStyle
    // which is not convenient since it can not be created manually
    // change/adapt API and usages, see convertObjectToRuleStyle
    addCSSRule({ selector, ruleStyle, whitelist }) {
        const IframeCSSStyleDeclaration = this.iframeWindow.CSSStyleDeclaration;
        if (!(ruleStyle instanceof IframeCSSStyleDeclaration)) {
            ruleStyle = this.convertObjectToRuleStyle(ruleStyle);
        }
        selector = selector.trim();
        const rule = this.getRule(selector);
        for (const property of whitelist ?? ruleStyle) {
            rule.style.setProperty(
                property,
                ruleStyle.getPropertyValue(property),
                ruleStyle.getPropertyPriority(property)
            );
        }
    }
}

export class CustomizeMailingVariable extends BuilderAction {
    static id = "mass_mailing_egg.CustomizeMailingVariable";
    static dependencies = ["builderActions", "mass_mailing.CustomizeMailingPlugin", "history"];
    isApplied({ value }) {
        return this.getValue(...arguments) === value;
    }
    /**
     * @param { Object } params
     * @param { string } params.selector
     * @param { string } params.property
     */
    getValue({ params }) {
        return this.dependencies["mass_mailing.CustomizeMailingPlugin"].getVariableValue(
            params.variable
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
}

registry.category("mass_mailing-plugins").add(CustomizeMailingPlugin.id, CustomizeMailingPlugin);
