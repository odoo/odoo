import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { StyleInfoMap } from "./style_models";

/**
 * TODO EGGMAIL: decide what to do about the styleSheet (it should be in the
 * head, but the head is generated in python)
 */
export class DynamicStyleSheetPlugin extends Plugin {
    static id = "dynamicStyleSheet";
    static shared = ["addToStyleSheet"];
    resources = {
        on_render_email_template_handlers: this.renderDynamicStyleSheet.bind(this),
    };

    setup() {
        this.rules = new StyleInfoMap();
        this.mediaRules = new Map();
        this.addToStyleSheet("body", {
            "font-family": "Arial,Helvetica Neue,Helvetica,sans-serif",
            margin: "0",
            padding: "0",
        });
        this.addToStyleSheet("a", {
            "text-decoration": "none",
        });
    }

    getMediaKey(maxWidth) {
        return `@media screen and (max-width: ${maxWidth}px)`;
    }

    getRules(maxWidth) {
        if (maxWidth === undefined) {
            return this.rules;
        }
        const mediaKey = this.getMediaKey(maxWidth);
        if (!this.mediaRules.has(mediaKey)) {
            this.mediaRules.set(mediaKey, new StyleInfoMap());
        }
        return this.mediaRules.get(mediaKey);
    }

    addToStyleSheet(selector, style, maxWidth) {
        const rules = this.getRules(maxWidth);
        rules.assign(style, selector);
    }

    renderRules(rules, aggregator, separator, indent) {
        for (const [selector, styleInfo] of rules) {
            const styleInfoSeparator = `${separator}${indent}`;
            aggregator.push(
                [`${selector} {`, `${indent}${styleInfo.serialize(styleInfoSeparator)}`, "}"].join(
                    separator
                )
            );
        }
    }

    /**
     * TODO EGGMAIL: minify style element (don't bother with newlines/padding)
     * maybe only in debug mode?
     */
    renderDynamicStyleSheet(template) {
        const styleEl = this.config.referenceDocument.createElement("STYLE");
        const cssTextArray = [];
        const indent = "    ";
        const separator = `\n`;
        this.renderRules(this.rules, cssTextArray, separator, indent);
        for (const [media, rules] of this.mediaRules) {
            const ruleSeparator = `${separator}${indent}`;
            const mediaCssTextArray = [];
            this.renderRules(rules, mediaCssTextArray, ruleSeparator, indent);
            cssTextArray.push(
                [`${media} {`, `${indent}${mediaCssTextArray.join(ruleSeparator)}`, "}"].join(
                    separator
                )
            );
        }
        styleEl.textContent = cssTextArray.join(separator);
        template.content.prepend(styleEl);
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(DynamicStyleSheetPlugin.id, DynamicStyleSheetPlugin);
