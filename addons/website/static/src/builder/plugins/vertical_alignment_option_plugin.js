import { VerticalAlignmentOption } from "@html_builder/plugins/vertical_alignment_option";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BOX_BORDER_SHADOW } from "../option_sequence";
import { registry } from "@web/core/registry";

class VerticalAlignmentOptionPlugin extends Plugin {
    static id = "websiteVerticalAlignmentOption";
    resources = {
        builder_options: [
            withSequence(BOX_BORDER_SHADOW, {
                OptionComponent: VerticalAlignmentOption,
                selector: ".s_attributes_horizontal_col",
                applyTo: ":scope > .row",
                props: {
                    level: 0,
                    justify: false,
                },
            }),
        ],
    };
}
registry
    .category("website-plugins")
    .add(VerticalAlignmentOptionPlugin.id, VerticalAlignmentOptionPlugin);
