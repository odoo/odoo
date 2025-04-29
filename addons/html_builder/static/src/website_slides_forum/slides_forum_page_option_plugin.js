import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class SlidesForumOptionPlugin extends Plugin {
    static id = "slidesForumOption";
    resources = {
        builder_options: [
            {
                template: "website_slides_forum.slidesForumOption",
                selector: "main:has(#o_wforum_forums_index_list)",
                editableOnly: false,
                title: _t("Slides Forum Snippet Options"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(SlidesForumOptionPlugin.id, SlidesForumOptionPlugin);
