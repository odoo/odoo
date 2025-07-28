import { BaseOptionComponent } from "@html_builder/core/utils";
import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class TimelineListOption extends BaseOptionComponent {
    static template = "website.TimelineListOption";
    static selector = ".s_timeline_list";
}

export class DotLinesColorOption extends BaseOptionComponent {
    static template = "website.DotLinesColorOption";
    static selector = ".s_timeline_list";
}

export class DotColorOption extends BaseOptionComponent {
    static template = "website.DotColorOption";
    static selector = ".s_timeline_list .s_timeline_list_row";
}

class TimelineListOptionPlugin extends Plugin {
    static id = "timelineListOption";
    resources = {
        builder_options: [
            // TODO AGAU: alignment option sequence doesn't match master, must split template
            withSequence(BEGIN, TimelineListOption),
            withSequence(SNIPPET_SPECIFIC_END, DotLinesColorOption),
            withSequence(BEGIN, DotColorOption),
        ],
        dropzone_selector: {
            selector: ".s_timeline_list_row",
            dropNear: ".s_timeline_list_row",
        },
        is_movable_selector: { selector: ".s_timeline_list_row", direction: "vertical" },
    };
}

registry.category("website-plugins").add(TimelineListOptionPlugin.id, TimelineListOptionPlugin);
