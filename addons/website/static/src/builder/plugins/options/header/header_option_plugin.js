import {
    SNIPPET_SPECIFIC_END,
    SNIPPET_SPECIFIC_NEXT,
    splitBetween,
} from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { HeaderElementsOption } from "./header_elements_option";
import { HeaderFontOption } from "./header_font_option";
import { HeaderTemplateOption } from "./header_template_option";
import { HeaderIconBackgroundOption } from "./header_icon_background_option";

const [
    HEADER_TEMPLATE,
    HEADER_FONT,
    HEADER_BOX,
    HEADER_NAVIGATION,
    HEADER_ELEMENTS,
    HEADER_ICON_BACKGROUND,
    HEADER_END,
    ...__ERROR_CHECK__
] = splitBetween(SNIPPET_SPECIFIC_NEXT, SNIPPET_SPECIFIC_END, 7);
if (__ERROR_CHECK__.length > 0) {
    console.error("Wrong count in header option split");
}

export {
    HEADER_TEMPLATE,
    HEADER_FONT,
    HEADER_BOX,
    HEADER_NAVIGATION,
    HEADER_ELEMENTS,
    HEADER_ICON_BACKGROUND,
    HEADER_END,
};

export const basicHeaderOptionSettings = {
    editableOnly: false,
    selector: "#wrapwrap > header",
    groups: ["website.group_website_designer"],
}

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: [
            withSequence(HEADER_TEMPLATE, {
                ...basicHeaderOptionSettings,
                OptionComponent: HeaderTemplateOption,
            }),
            withSequence(HEADER_FONT, {
                ...basicHeaderOptionSettings,
                OptionComponent: HeaderFontOption,
            }),
            withSequence(HEADER_ELEMENTS, {
                ...basicHeaderOptionSettings,
                OptionComponent: HeaderElementsOption,
            }),
            withSequence(HEADER_ICON_BACKGROUND, {
                ...basicHeaderOptionSettings,
                OptionComponent: HeaderIconBackgroundOption,
            }),
        ],
    };
};

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
