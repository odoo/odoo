import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";

const RE_SELECTOR_ENDS_WITH_GT_STAR = />\s*\*\s*$/;

export class CustomizeMailingPlugin extends Plugin {
    static id = "mass_mailing.CustomizeMailingPlugin";
    static dependencies = [];
    static shared = [
        "addCSSRule",
        "convertObjectToRuleStyle",
        "getRule",
        "transformFontFamilySelector",
    ];

    resources = {
        builder_actions: {
            CustomizeStyleProperty,
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
        for (const style of whitelist ?? ruleStyle) {
            rule.style.setProperty(
                style,
                ruleStyle.getPropertyValue(style),
                ruleStyle.getPropertyPriority(style)
            );
        }
    }
}

export const PRIORITY_STYLES = {
    h1: new Set(["font-family"]),
    h2: new Set(["font-family"]),
    h3: new Set(["font-family"]),
    p: new Set(["font-family"]),
    hr: new Set(["border-top-width", "border-top-style", "border-top-color"]),
};

export class CustomizeStyleProperty extends BuilderAction {
    static id = "mass_mailing_egg.CustomizeStyleProperty";
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
        const rule = this.dependencies["mass_mailing.CustomizeMailingPlugin"].getRule(
            params.selector
        );
        return rule.style.getPropertyValue(params.property);
    }
    apply({ params, value }) {
        const oldValue = this.getValue(...arguments);
        const important = PRIORITY_STYLES[params.selector]?.has(params.property);
        this.dependencies.history.applyCustomMutation({
            apply: () => {
                for (const selector of [params.selector, ...(params.extraSelectors ?? [])]) {
                    this.dependencies["mass_mailing.CustomizeMailingPlugin"].addCSSRule({
                        selector,
                        ruleStyle: {
                            [params.property]: `${value}${important ? "!important" : ""};`,
                        },
                    });
                }
            },
            revert: () => {
                for (const selector of [params.selector, ...(params.extraSelectors ?? [])]) {
                    this.dependencies["mass_mailing.CustomizeMailingPlugin"].addCSSRule({
                        selector,
                        ruleStyle: {
                            [params.property]: `${oldValue}${important ? "!important" : ""};`,
                        },
                    });
                }
            },
        });
    }
}

registry.category("mass_mailing-plugins").add(CustomizeMailingPlugin.id, CustomizeMailingPlugin);
