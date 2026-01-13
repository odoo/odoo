import { after, FONT_AWESOME } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { FaStyleOption } from "@website/builder/plugins/fa_style_option";

export class FaStyleOptionPlugin extends Plugin {
    static id = "faStyleOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(after(FONT_AWESOME), FaStyleOption)],
    };
}

registry.category("builder-plugins").add(FaStyleOptionPlugin.id, FaStyleOptionPlugin);
