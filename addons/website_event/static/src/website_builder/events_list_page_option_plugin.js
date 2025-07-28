import { BaseOptionComponent } from "@html_builder/core/utils";
import { DEFAULT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class EventsListPageOption extends BaseOptionComponent {
    static template = "website_event.EventsListPageOption";
    static selector = "main:has(.o_wevent_events_list)";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class EventsListPageOptionPlugin extends Plugin {
    static id = "eventsListPageOption";
    resources = {
        builder_options: [
            withSequence(DEFAULT, EventsListPageOption),
        ],
    };
}

registry.category("website-plugins").add(EventsListPageOptionPlugin.id, EventsListPageOptionPlugin);
