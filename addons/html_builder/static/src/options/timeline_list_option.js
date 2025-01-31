import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class TimelineListOptionPlugin extends Plugin {
    static id = "TimelineListOption";
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.TimelineListOption",
                selector: ".s_timeline_list",
            }),
            withSequence(10, {
                template: "html_builder.DotLinesColorOption",
                selector: ".s_timeline_list",
            }),
            withSequence(5, {
                template: "html_builder.DotColorOption",
                selector: ".s_timeline_list .s_timeline_list_row",
            }),
        ],
        dropzone_selector: {
            selector: ".s_timeline_list_row",
            dropNear: ".s_timeline_list_row",
        },
    };
}

registry.category("website-plugins").add(TimelineListOptionPlugin.id, TimelineListOptionPlugin);
