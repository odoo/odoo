import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class EventsListPageOptionPlugin extends Plugin {
    static id = "eventsListPageOption";
    resources = {
        builder_options: [
            {
                template: "website_event.EventsListPageOption",
                selector: "main:has(.o_wevent_events_list)",
                editableOnly: false,
            },
        ],
    };
}

registry.category("website-plugins").add(EventsListPageOptionPlugin.id, EventsListPageOptionPlugin);
