import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class EventSearchbarOptionPlugin extends Plugin {
    static id = "eventSearchbarOption";

    resources = {
        searchbar_option_order_by_items: [
            {
                label: _t("Date (old to new)"),
                orderBy: "date_begin asc",
                dependency: "search_events_opt",
            },
            {
                label: _t("Date (new to old)"),
                orderBy: "date_end desc",
                dependency: "search_events_opt",
            },
        ],
        searchbar_option_display_items: [
            {
                label: _t("Description"),
                dataAttribute: "displayDescription",
                dependency: "search_events_opt",
            },
            {
                label: _t("Event Date"),
                dataAttribute: "displayDetail",
                dependency: "search_events_opt",
            },
        ],
    };
}

registry.category("website-plugins").add(EventSearchbarOptionPlugin.id, EventSearchbarOptionPlugin);
