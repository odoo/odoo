import { DEFAULT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BaseOptionComponent } from "@html_builder/core/utils";

export const FORUMS_INDEX = DEFAULT;

export class ForumPageOption extends BaseOptionComponent {
    static template = "website_forum.forumPageOption";
    static selector = "main:has(#o_wforum_forums_index_list)";
    static title = _t("Forum Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class ForumPageOptionPlugin extends Plugin {
    static id = "forumPageOption";
    resources = {
        builder_options: [
            withSequence(FORUMS_INDEX, ForumPageOption),
        ],
    };
}

registry.category("website-plugins").add(ForumPageOptionPlugin.id, ForumPageOptionPlugin);
