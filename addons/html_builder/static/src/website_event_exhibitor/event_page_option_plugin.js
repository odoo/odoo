import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class EventPageOption extends Plugin {
    static id = "eventExhibitorPageOption";
    resources = {
        builder_options: [
            withSequence(15, {
                template: "website_event_exhibitor.EventPageFilterOption",
                selector: "main:has(.o_wevent_event_tags_form)",
                editableOnly: false,
            }),
            withSequence(20, {
                template: "website_event_exhibitor.EventPageOption",
                selector: "main:has(.o_wevent_event)",
                editableOnly: false,
            }),
        ],
    };
}

registry.category("website-plugins").add(EventPageOption.id, EventPageOption);
