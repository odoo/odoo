/** @odoo-module **/
import {
    Box,
} from "@web_editor/js/editor/snippets.options";
import {
    registerWebsiteOption
} from "@website/js/editor/snippets.registry";
import { 
    websiteRegisterBackgroundOptions, 
} from "@website/js/editor/snippets.options";

registerWebsiteOption("Blockquote (layout)", {
    template: "website.s_blockquote_option_layout",
    selector: ".s_blockquote",
});
websiteRegisterBackgroundOptions("Blockquote (background)", {
        selector: ".s_blockquote",
        withColors: true,
        withImages: true,
        withShapes: true,
        withGradients: true,
});
registerWebsiteOption("Blockquote (border)", {
    Class: Box,
    template: "website.snippet_options_border_widgets",
    selector: ".s_blockquote",
});
registerWebsiteOption("Blockquote (shadow)", {
    Class: Box,
    template: "website.snippet_options_shadow_widgets",
    selector: ".s_blockquote",
});
