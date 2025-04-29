import { TRACK } from "@website_event/website_builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class EventTrackPageOption extends Plugin {
    static id = "eventTrackPageOption";
    resources = {
        builder_options: [
            withSequence(TRACK, {
                template: "website_event_track.eventTrackPageOptionTopbar",
                selector: "main:has(.o_weagenda_topbar_filters)",
                title: _t("Event Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
            withSequence(TRACK, {
                template: "website_event_track.EventTrackPageOption",
                selector: "main:has(.o_wesession_index)",
                title: _t("Event Page"),
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(EventTrackPageOption.id, EventTrackPageOption);
