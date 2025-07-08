import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";

const RE_SELECTOR_ENDS_WITH_GT_STAR = />\s*\*\s*$/;

export class CustomizeMailingPlugin extends Plugin {
    static id = "mass_mailing.CustomizeMailingPlugin";
    static dependencies = [];
    static shared = ["addCSSRule", "getRule", "transformFontFamilySelector"];

    resources = {
        builder_actions: {
            MailWrapperMaxWidthAction,
            CustomizeLayoutColorAction,
            CustomizeSnippetColorAction,
        },
        mass_mailing_css_prefix_selectors: ".o_mail_wrapper",
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };
    getRule = memoize((selector) => this._getRule(selector));

    setup() {
        this.iframeWindow = this.document.defaultView;
        this.cssPrefix = this.getResource("mass_mailing_css_prefix_selectors").join(",");
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

    parseDesignElement(styleEl) {
        const rules = [...styleEl.sheet.cssRules];
        for (const rule of rules) {
            for (let selector of rule.selectorText.split(",")) {
                if (!selector.trim().startsWith(this.cssPrefix)) {
                    selector = `${this.cssPrefix} ${selector.trim()}`;
                }
                for (const style of rule.style) {
                    let selectors = [selector];
                    if (style === "font-family") {
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
    // change/adapt API and usages
    addCSSRule({ selector, ruleStyle, whitelist }) {
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

const BODY_WIDTH_CLASSES = new Set(["o_mail_small", "o_mail_regular"]);
export class MailWrapperMaxWidthAction extends BuilderAction {
    static id = "mass_mailing_egg.MailWrapperMaxWidthAction";
    static dependencies = ["builderActions"];
    setup() {
        this.mailWrapper = this.editable.querySelector(".o_mail_wrapper");
    }
    isApplied({ value }) {
        return this.getValue() === value;
    }
    getValue() {
        for (const className of BODY_WIDTH_CLASSES) {
            if (this.mailWrapper.matches(`.${className}`)) {
                return className;
            }
        }
        return "";
    }
    apply({ value }) {
        const currentValue = this.getValue();
        if (currentValue === value) {
            return;
        }
        if (currentValue) {
            this.mailWrapper.classList.remove(currentValue);
        }
        if (value) {
            this.mailWrapper.classList.add(value);
        }
    }
}

export class CustomizeLayoutColorAction extends BuilderAction {
    static id = "mass_mailing_egg.CustomizeLayoutColorAction";
    static dependencies = ["builderActions"];
    setup() {
        this.layoutEl = this.editable.querySelector(".o_layout");
    }
    isApplied({ value }) {
        return this.getValue() === value;
    }
    getValue() {
        return this.layoutEl.style.backgroundColor;
    }
    apply({ value }) {
        this.layoutEl.style.backgroundColor = value;
    }
}

// TODO EGGMAIL: verify this selector
const WRAPPER_SNIPPET_SELECTOR = ".o_mail_wrapper_td > [data-snippet]";
export class CustomizeSnippetColorAction extends BuilderAction {
    static id = "mass_mailing_egg.CustomizeSnippetColorAction";
    static dependencies = ["builderActions", "mass_mailing.CustomizeMailingPlugin", "history"];
    isApplied({ value }) {
        return this.getValue() === value;
    }
    getValue() {
        const rule =
            this.dependencies["mass_mailing.CustomizeMailingPlugin"].getRule(
                WRAPPER_SNIPPET_SELECTOR
            );
        return rule.style.backgroundColor;
    }
    apply({ value }) {
        const oldValue = this.getValue();
        const customMutation = {
            apply: () => {
                const ruleStyle = ["background-color"];
                // TODO EGGMAIL: hack to go forward, change API of addCSSRule
                ruleStyle.getPropertyPriority = () => "important";
                ruleStyle.getPropertyValue = () => value;
                this.dependencies["mass_mailing.CustomizeMailingPlugin"].addCSSRule({
                    selector: WRAPPER_SNIPPET_SELECTOR,
                    ruleStyle,
                });
            },
            revert: () => {
                const ruleStyle = ["background-color"];
                // TODO EGGMAIL: hack to go forward, change API of addCSSRule
                ruleStyle.getPropertyPriority = () => "important";
                ruleStyle.getPropertyValue = () => oldValue;
                this.dependencies["mass_mailing.CustomizeMailingPlugin"].addCSSRule({
                    selector: WRAPPER_SNIPPET_SELECTOR,
                    ruleStyle,
                });
            },
        };
        customMutation.apply();
        this.dependencies.history.addCustomMutation(customMutation);
        // TODO EGGMAIL: do we want that ? Overwrite the custom style of every snippet?
        for (const snippetEl of [...this.editable.querySelectorAll(WRAPPER_SNIPPET_SELECTOR)]) {
            snippetEl.style["background-color"] = "";
        }
    }
}

registry.category("mass_mailing-plugins").add(CustomizeMailingPlugin.id, CustomizeMailingPlugin);
