import { BaseOptionComponent } from "@html_builder/core/utils";
import { BEGIN, SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class TimelineImagesOption extends BaseOptionComponent {
    static template = "website.TimelineImagesOption";
    static selector = ".s_timeline_images";
}

export class DotLinesColorOption extends BaseOptionComponent {
    static template = "website.DotLinesColorOption";
    static selector = ".s_timeline_images";
}

export class DotColorOption extends BaseOptionComponent {
    static template = "website.DotColorOption";
    static selector = ".s_timeline_images .s_timeline_images_row";
}

class TimelineImagesOptionPlugin extends Plugin {
    static id = "timelineImagesOption";
    resources = {
        builder_options: [
            withSequence(BEGIN, TimelineImagesOption),
            withSequence(SNIPPET_SPECIFIC_END, DotLinesColorOption),
            withSequence(SNIPPET_SPECIFIC, DotColorOption),
        ],
        dropzone_selector: {
            selector: ".s_timeline_images_row",
            dropNear: ".s_timeline_images_row",
        },
        is_movable_selector: { selector: ".s_timeline_images_row", direction: "vertical" },
    };
}

registry.category("website-plugins").add(TimelineImagesOptionPlugin.id, TimelineImagesOptionPlugin);
