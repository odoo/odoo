import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class TimelineListOptionPlugin extends Plugin {
    static id = "timelineListOption";
    resources = {
        builder_options: [
            // TODO AGAU: alignment option sequence doesn't match master, must split template
            withSequence(BEGIN, {
                template: "website.TimelineListOption",
                selector: ".s_timeline_list",
            }),
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.DotLinesColorOption",
                selector: ".s_timeline_list",
            }),
            withSequence(BEGIN, {
                template: "website.DotColorOption",
                selector: ".s_timeline_list .s_timeline_list_row",
            }),
        ],
        dropzone_selector: {
            selector: ".s_timeline_list_row",
            dropNear: ".s_timeline_list_row",
        },
        is_movable_selector: { selector: ".s_timeline_list_row", direction: "vertical" },
    };
}

registry.category("website-plugins").add(TimelineListOptionPlugin.id, TimelineListOptionPlugin);
