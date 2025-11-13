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
    resources = {
        builder_options: [withSequence(BEGIN, FaqHorizontalOption)],
    };
}
registry.category("website-plugins").add(FaqHorizontalOptionPlugin.id, FaqHorizontalOptionPlugin);
