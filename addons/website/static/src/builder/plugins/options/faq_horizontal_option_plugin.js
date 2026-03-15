import { BaseOptionComponent } from "@html_builder/core/utils";
import { BEGIN } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class FaqHorizontalOption extends BaseOptionComponent {
    static template = "website.FaqHorizontalOption";
    static selector = ".s_faq_horizontal";
}

class FaqHorizontalOptionPlugin extends Plugin {
    static id = "faqHorizontalOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(BEGIN, FaqHorizontalOption)],
        dropzone_selector: {
            selector: ".s_faq_horizontal",
            excludeAncestor: ".s_table_of_content",
        },
    };
}
registry.category("website-plugins").add(FaqHorizontalOptionPlugin.id, FaqHorizontalOptionPlugin);
