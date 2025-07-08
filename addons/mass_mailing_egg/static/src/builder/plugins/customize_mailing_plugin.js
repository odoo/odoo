import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const RE_SELECTOR_ENDS_WITH_GT_STAR = />\s*\*\s*$/;

export class CustomizeMailingPlugin extends Plugin {
    static id = "mass_mailing.CustomizeMailing_plugin";
    static dependencies = [];
    static shared = ["transformFontFamilySelector"];

    resources = {
        mass_mailing_css_prefix_selectors: ".o_mail_wrapper",
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
    };

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
        styleEl.textContent = Array.from(this.styleSheet.cssRules)
            .map((rule) => rule.cssText)
            .join("\n");
        layoutEl.prepend(styleEl);
    }

    parseDesignElement(styleEl) {
        const rules = [...styleEl.sheet.cssRules];
        const stylesToWrite = {};
        for (const rule of rules) {
            const styles = rule.style;
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
                    for (const selectorToWriteTo of selectors) {
                        if (!stylesToWrite[selectorToWriteTo]) {
                            stylesToWrite[selectorToWriteTo] = [];
                        }
                        stylesToWrite[selectorToWriteTo].push([
                            style,
                            styles[style] +
                                (styles.getPropertyPriority(style) === "important"
                                    ? " !important"
                                    : ""),
                        ]);
                    }
                }
            }
        }
        for (const [selector, styles] of Object.entries(stylesToWrite)) {
            this.styleSheet.insertRule(
                `${selector.trim()} { ${styles
                    .map(([styleName, style]) => `${styleName}: ${style};`)
                    .join(" ")} }`
            );
        }
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
}

registry.category("mass_mailing-plugins").add(CustomizeMailingPlugin.id, CustomizeMailingPlugin);
