import { ALIGNMENT_STYLE_PADDING } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { WebsiteImageAndFaOption } from "@website/builder/plugins/image/image_and_fa_option";

class WebsiteImageAndFaOptionPlugin extends Plugin {
    static id = "website.ImageAndFaOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(ALIGNMENT_STYLE_PADDING, WebsiteImageAndFaOption)],
    };
}

registry
    .category("builder-plugins")
    .add(WebsiteImageAndFaOptionPlugin.id, WebsiteImageAndFaOptionPlugin);
