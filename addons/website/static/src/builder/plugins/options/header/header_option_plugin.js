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
import { HeaderTopOptions } from "./header_top_options";

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

class HeaderOptionPlugin extends Plugin {
    static id = "headerOption";
    static dependencies = ["customizeWebsite", "menuDataPlugin"];

    resources = {
        builder_header_middle_buttons: [
            {
                Component: HeaderTopOptions,
                editableOnly: false,
                selector: "#wrapwrap > header",
                props: {
                    openEditMenu: () => this.dependencies.menuDataPlugin.openEditMenu(),
                },
            },
        ],
        builder_options: [
            withSequence(HEADER_TEMPLATE, HeaderTemplateOption),
            withSequence(HEADER_FONT, HeaderFontOption),
            withSequence(HEADER_ELEMENTS, HeaderElementsOption),
            withSequence(HEADER_ICON_BACKGROUND, HeaderIconBackgroundOption),
        ],
    };
}

registry.category("website-plugins").add(HeaderOptionPlugin.id, HeaderOptionPlugin);
