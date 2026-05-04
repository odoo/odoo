import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class ForumFloatingSnippetsPlugin extends Plugin {
    static id = "forumFloatingSnippets";

    resources = {
        floating_snippet_scope_providers: withSequence(20, {
            value: "allForums",
            label: _t("All Forums"),
            containerSelector:
                "#oe_structure_website_forum_footer_1, #oe_structure_website_forum_header_1, #oe_structure_website_forum_header_2",
        }),
    };
}

registry.category("website-plugins").add(ForumFloatingSnippetsPlugin.id, ForumFloatingSnippetsPlugin);
