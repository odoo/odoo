import { DEFAULT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export const FORUMS_INDEX = DEFAULT;

class ForumPageOptionPlugin extends Plugin {
    static id = "forumPageOption";
    resources = {
        builder_options: [
            withSequence(FORUMS_INDEX, {
                template: "website_forum.forumPageOption",
                selector: "main:has(#o_wforum_forums_index_list)",
                editableOnly: false,
                title: _t("Forum Page"),
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(ForumPageOptionPlugin.id, ForumPageOptionPlugin);
