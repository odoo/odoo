import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class FaqHorizontalOptionPlugin extends Plugin {
    static id = "faqHorizontalOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_faq_horizontal",
            excludeAncestor: ".s_table_of_content",
        },
    };
}
registry.category("website-plugins").add(FaqHorizontalOptionPlugin.id, FaqHorizontalOptionPlugin);
