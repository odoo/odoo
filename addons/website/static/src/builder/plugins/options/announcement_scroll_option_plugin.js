import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { after } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";

class AnnouncementScrollOptionPlugin extends Plugin {
    static id = "announcementScrollOptionPlugin";
    static dependencies = ["edit_interaction", "builderOptions"];
    selector = "section.s_announcement_scroll";
    resources = {
        builder_options: [
            withSequence(after(WEBSITE_BACKGROUND_OPTIONS), {
                template: "website.AnnouncementScrollOption",
                selector: this.selector,
            }),
        ],
    };
}

registry.category("website-plugins").add(AnnouncementScrollOptionPlugin.id, AnnouncementScrollOptionPlugin);
