import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { after, SNIPPET_SPECIFIC_NEXT } from "@html_builder/utils/option_sequence";

export const HEADER_TEMPLATE = SNIPPET_SPECIFIC_NEXT;
export const HEADER_SCROLL_EFFECT = after(SNIPPET_SPECIFIC_NEXT);
export const HEADER_ELEMENT = after(HEADER_SCROLL_EFFECT);

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";

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
        ],
    };
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
