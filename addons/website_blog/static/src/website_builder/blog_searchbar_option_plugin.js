import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class BlogSearchbarOptionPlugin extends Plugin {
    static id = "blogSearchbarOption";

    resources = {
        searchbar_option_order_by_items: [
            {
                label: _t("Date (old to new)"),
                orderBy: "published_date asc",
                dependency: "search_blogs_opt",
            },
            {
                label: _t("Date (new to old)"),
                orderBy: "published_date desc",
                dependency: "search_blogs_opt",
            },
        ],
        searchbar_option_display_items: [
            {
                label: _t("Description"),
                dataAttribute: "displayDescription",
                dependency: "search_blogs_opt",
            },
            {
                label: _t("Publication Date"),
                dataAttribute: "displayDetail",
                dependency: "search_blogs_opt",
            },
        ],
    };
}

registry.category("website-plugins").add(BlogSearchbarOptionPlugin.id, BlogSearchbarOptionPlugin);
