import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class ForumSearchbarOptionPlugin extends Plugin {
    static id = "forumSearchbarOption";

    resources = {
        searchbar_option_order_by_items: [
            {
                label: _t("Date (old to new)"),
                orderBy: "write_date asc",
                dependency: "search_forums_opt",
            },
            {
                label: _t("Date (new to old)"),
                orderBy: "write_date desc",
                dependency: "search_forums_opt",
            },
        ],
        searchbar_option_display_items: [
            {
                label: _t("Description"),
                dataAttribute: "displayDescription",
                dependency: "search_forums_opt",
            },
            {
                label: _t("Date"),
                dataAttribute: "displayDetail",
                dependency: "search_forums_opt",
            },
        ],
    };
}

registry.category("website-plugins").add(ForumSearchbarOptionPlugin.id, ForumSearchbarOptionPlugin);
