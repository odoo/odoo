import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class ForumPageOptionPlugin extends Plugin {
    static id = "forumPageOption";
    resources = {
        builder_options: [
            {
                template: "website_forum.forumPageOption",
                selector: "main:has(#o_wforum_forums_index_list)",
                editableOnly: false,
                title: _t("Forum Page"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry.category("website-plugins").add(ForumPageOptionPlugin.id, ForumPageOptionPlugin);
