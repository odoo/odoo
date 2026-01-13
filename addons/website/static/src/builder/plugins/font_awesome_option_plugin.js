import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { FONT_AWESOME } from "@html_builder/utils/option_sequence";
import { WebsiteFontAwesomeOption } from "@website/builder/plugins/font_awesome_option";

class WebsiteFontAwesomeOptionPlugin extends Plugin {
    static id = "website.FontAwesomeOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(FONT_AWESOME, WebsiteFontAwesomeOption)],
    };
}

registry
    .category("builder-plugins")
    .add(WebsiteFontAwesomeOptionPlugin.id, WebsiteFontAwesomeOptionPlugin);
