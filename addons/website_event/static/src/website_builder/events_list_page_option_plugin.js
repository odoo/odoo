import { DEFAULT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class EventsListPageOptionPlugin extends Plugin {
    static id = "eventsListPageOption";
    resources = {
        builder_options: [
            withSequence(DEFAULT, {
                template: "website_event.EventsListPageOption",
                selector: "main:has(.o_wevent_events_list)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(EventsListPageOptionPlugin.id, EventsListPageOptionPlugin);
