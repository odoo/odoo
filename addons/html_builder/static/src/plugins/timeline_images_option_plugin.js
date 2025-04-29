import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class TimelineImagesOptionPlugin extends Plugin {
    static id = "timelineImagesOption";
    static dependencies = ["history"];
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.TimelineImagesOption",
                selector: ".s_timeline_images",
            }),
            withSequence(10, {
                template: "html_builder.DotLinesColorOption",
                selector: ".s_timeline_images",
            }),
            withSequence(5, {
                template: "html_builder.DotColorOption",
                selector: ".s_timeline_images .s_timeline_images_row",
            }),
        ],
        dropzone_selector: {
            selector: ".s_timeline_images_row",
            dropNear: ".s_timeline_images_row",
        },
    };
}

registry.category("website-plugins").add(TimelineImagesOptionPlugin.id, TimelineImagesOptionPlugin);
