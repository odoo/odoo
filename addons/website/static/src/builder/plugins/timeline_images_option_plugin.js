import { BEGIN, SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class TimelineImagesOptionPlugin extends Plugin {
    static id = "timelineImagesOption";
    static dependencies = ["history"];
    resources = {
        builder_options: [
            withSequence(BEGIN, {
                template: "website.TimelineImagesOption",
                selector: ".s_timeline_images",
            }),
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.DotLinesColorOption",
                selector: ".s_timeline_images",
            }),
            withSequence(SNIPPET_SPECIFIC, {
                template: "website.DotColorOption",
                selector: ".s_timeline_images .s_timeline_images_row",
            }),
        ],
        dropzone_selector: {
            selector: ".s_timeline_images_row",
            dropNear: ".s_timeline_images_row",
        },
        is_movable_selector: { selector: ".s_timeline_images_row", direction: "vertical" },
    };
}

registry.category("website-plugins").add(TimelineImagesOptionPlugin.id, TimelineImagesOptionPlugin);
