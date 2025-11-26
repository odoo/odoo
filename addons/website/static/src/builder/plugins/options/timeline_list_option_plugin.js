import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TimelineListOptionPlugin extends Plugin {
    static id = "timelineListOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_timeline_list_row",
            dropNear: ".s_timeline_list_row",
        },
        is_movable_selector: { selector: ".s_timeline_list_row", direction: "vertical" },
    };
}

registry.category("website-plugins").add(TimelineListOptionPlugin.id, TimelineListOptionPlugin);
