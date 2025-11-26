import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TimelineImagesOptionPlugin extends Plugin {
    static id = "timelineImagesOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dropzone_selector: {
            selector: ".s_timeline_images_row",
            dropNear: ".s_timeline_images_row",
        },
        is_movable_selector: { selector: ".s_timeline_images_row", direction: "vertical" },
    };
}

registry.category("website-plugins").add(TimelineImagesOptionPlugin.id, TimelineImagesOptionPlugin);
