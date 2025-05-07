import { after } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BentoBannerOptionPlugin extends Plugin {
    static id = "bentoBannerOption";
    resources = {
        builder_options: [
            withSequence(after(WEBSITE_BACKGROUND_OPTIONS), {
                template: "html_builder.BentoBannerOption",
                selector: ".s_bento_banner section[data-name='Card']",
            }),
        ],
    };
}
registry.category("website-plugins").add(BentoBannerOptionPlugin.id, BentoBannerOptionPlugin);
