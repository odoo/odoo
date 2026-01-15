import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class SlidesSearchbarOptionPlugin extends Plugin {
    static id = "slidesSearchbarOption";

    resources = {
        searchbar_option_order_by_items: [
            {
                label: _t("Date (old to new)"),
                orderBy: "slide_last_update asc",
                dependency: "search_slides_opt",
            },
            {
                label: _t("Date (new to old)"),
                orderBy: "slide_last_update desc",
                dependency: "search_slides_opt",
            },
        ],
        searchbar_option_display_items: [
            {
                label: _t("Description"),
                dataAttribute: "displayDescription",
                dependency: "search_slides_opt",
            },
            {
                label: _t("Publication Date"),
                dataAttribute: "displayDetail",
                dependency: "search_slides_opt",
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(SlidesSearchbarOptionPlugin.id, SlidesSearchbarOptionPlugin);
