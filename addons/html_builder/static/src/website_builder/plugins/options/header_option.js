import {
    getCurrentShadow,
    getDefaultShadow,
    shadowToString,
} from "@html_builder/plugins/shadow_option_plugin";
import { after, SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { HeaderBorderOption } from "./header_border_option";

export const HEADER_TEMPLATE = SNIPPET_SPECIFIC_NEXT;
export const HEADER_SCROLL_EFFECT = after(SNIPPET_SPECIFIC_NEXT);
export const HEADER_ELEMENT = after(HEADER_SCROLL_EFFECT);
export const HEADER_BORDER = after(HEADER_ELEMENT);

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["coreBuilderAction", "customizeWebsite", "shadowOption"];

    resources = {
        builder_options: [
            withSequence(HEADER_TEMPLATE, {
                editableOnly: false,
                template: "website.headerTemplateOption",
                selector: "header",
                groups: ["website.group_website_designer"],
            }),
            // TODO Header box (border & shadow) ?
            withSequence(HEADER_SCROLL_EFFECT, {
                editableOnly: false,
                template: "website.headerScrollEffectOption",
                selector: "#wrapwrap > header",
                groups: ["website.group_website_designer"],
            }),
            withSequence(HEADER_ELEMENT, {
                editableOnly: false,
                template: "website.headerElementOption",
                selector: "header",
                groups: ["website.group_website_designer"],
            }),
            withSequence(HEADER_BORDER, {
                editableOnly: false,
                OptionComponent: HeaderBorderOption,
                selector: "#wrapwrap > header",
                applyTo: ".navbar:not(.d-none)",
                groups: ["website.group_website_designer"],
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        const styleAction = this.dependencies.coreBuilderAction.getStyleAction();
        const { setShadowMode, setShadow } = this.dependencies.shadowOption.getActions();
        const withCustomHistory = this.dependencies.customizeWebsite.withCustomHistory;
        return {
            styleActionHeader: withCustomHistory({
                ...styleAction,
                getValue: (...args) => {
                    const { params } = args[0];
                    const value = styleAction.getValue(...args);
                    if (params.mainParam === "border-width") {
                        return value.replace(/(^|\s)0px/gi, "").trim() || value;
                    }
                    return value;
                },
                apply: async ({ params, value }) => {
                    const styleName = params.mainParam;

                    if (styleName === "border-color") {
                        return this.dependencies.customizeWebsite.customizeWebsiteColors({
                            "menu-border-color": value,
                        });
                    }
                    return this.dependencies.customizeWebsite.customizeWebsiteVariables({
                        [`menu-${styleName}`]: value,
                    });
                },
            }),
            setShadowModeHeader: withCustomHistory({
                ...setShadowMode,
                preview: false,
                apply: ({ value: shadowMode }) => {
                    const defaultShadow =
                        shadowMode === "none" ? "none" : getDefaultShadow(shadowMode);
                    return this.dependencies.customizeWebsite.customizeWebsiteVariables({
                        "menu-box-shadow": defaultShadow,
                    });
                },
            }),
            setShadowHeader: withCustomHistory({
                ...setShadow,
                preview: false,
                apply: ({ editingElement, params: { mainParam: attributeName }, value }) => {
                    const shadow = getCurrentShadow(editingElement);
                    shadow[attributeName] = value;

                    return this.dependencies.customizeWebsite.customizeWebsiteVariables({
                        "menu-box-shadow": shadowToString(shadow),
                    });
                },
            }),
        };
    }
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
