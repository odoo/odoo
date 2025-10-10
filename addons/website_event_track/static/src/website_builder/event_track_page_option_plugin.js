import { TRACK } from "@website_event/website_builder/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class EventTrackPageOptionTopbar extends BaseOptionComponent {
    static template = "website_event_track.eventTrackPageOptionTopbar";
    static selector = "main:has(.o_weagenda_topbar_filters)";
    static title = _t("Event Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class EventTrackPageOption extends BaseOptionComponent {
    static template = "website_event_track.EventTrackPageOption";
    static selector = "main:has(.o_wesession_index)";
    static title = _t("Event Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class EventTrackPageOptionPlugin extends Plugin {
    static id = "eventTrackPageOption";
    resources = {
        builder_options: [
            withSequence(TRACK, EventTrackPageOptionTopbar),
            withSequence(TRACK, EventTrackPageOption),
        ],
    };
}

registry.category("website-plugins").add(EventTrackPageOptionPlugin.id, EventTrackPageOptionPlugin);
