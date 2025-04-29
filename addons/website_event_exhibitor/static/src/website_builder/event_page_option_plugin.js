import { EXHIBITOR_FILTER, SPONSOR } from "@website_event/website_builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class EventPageOption extends Plugin {
    static id = "eventExhibitorPageOption";
    resources = {
        builder_options: [
            withSequence(EXHIBITOR_FILTER, {
                template: "website_event_exhibitor.EventPageFilterOption",
                selector: "main:has(.o_wevent_event_tags_form)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(SPONSOR, {
                template: "website_event_exhibitor.EventPageOption",
                selector: "main:has(.o_wevent_event)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(EventPageOption.id, EventPageOption);
