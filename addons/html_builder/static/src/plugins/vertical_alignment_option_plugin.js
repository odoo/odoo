import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { VerticalAlignmentOption } from "@html_builder/plugins/vertical_alignment_option";
import { withSequence } from "@html_editor/utils/resource";
import { VERTICAL_ALIGNMENT } from "@html_builder/utils/option_sequence";

class VerticalAlignmentOptionPlugin extends Plugin {
    static id = "verticalAlignmentOption";
    resources = {
        builder_options: [
            withSequence(VERTICAL_ALIGNMENT, {
                OptionComponent: VerticalAlignmentOption,
                selector:
                    ".s_text_image, .s_image_text, .s_three_columns, .s_showcase, .s_numbers, .s_faq_collapse, .s_references, .s_accordion_image, .s_shape_image",
                applyTo: ".row",
                props: {
                    level: 1,
                },
            }),
        ],
        builder_actions: {
            SetVerticalAlignmentAction,
        },
    };
}

export class SetVerticalAlignmentAction extends ClassAction {
    static id = "setVerticalAlignment";
    getPriority({ params: { mainParam: classNames } = { mainParam: "" } }) {
        return classNames === "align-items-stretch" ? 0 : 1;
    }
    isApplied({ params: { mainParam: classNames } }) {
        if (classNames === "align-items-stretch") {
            return true;
        }
        return super.isApplied(...arguments);
    }
}

registry
    .category("website-plugins")
    .add(VerticalAlignmentOptionPlugin.id, VerticalAlignmentOptionPlugin);
