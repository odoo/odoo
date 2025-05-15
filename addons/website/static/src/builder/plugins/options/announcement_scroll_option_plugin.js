import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { after } from "@html_builder/utils/option_sequence";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
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
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            setDatasetIfUndefined(snippetEl, 'scrollcontent', '• Free Shipping • Secure payment • Easy Return');
        }
    }
}

registry.category("website-plugins").add(AnnouncementScrollOptionPlugin.id, AnnouncementScrollOptionPlugin);
