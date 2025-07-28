import { EXHIBITOR_FILTER, SPONSOR } from "@website_event/website_builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class EventPageFilterOption extends BaseOptionComponent {
    static template = "website_event_exhibitor.EventPageFilterOption";
    static selector = "main:has(.o_wevent_event_tags_form)";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class EventPageOption extends BaseOptionComponent {
    static template = "website_event_exhibitor.EventPageOption";
    static selector = "main:has(.o_wevent_event)";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class EventPageOptionPlugin extends Plugin {
    static id = "eventExhibitorPageOption";
    resources = {
        builder_options: [
            withSequence(EXHIBITOR_FILTER, EventPageFilterOption),
            withSequence(SPONSOR, EventPageOption),
        ],
    };
}

registry.category("website-plugins").add(EventPageOptionPlugin.id, EventPageOptionPlugin);
