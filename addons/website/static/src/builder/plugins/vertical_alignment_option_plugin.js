import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { classAction } from "@html_builder/core/core_builder_action_plugin";
import { VerticalAlignmentOption } from "./vertical_alignment_option";
import { withSequence } from "@html_editor/utils/resource";
import { VERTICAL_ALIGNMENT, BOX_BORDER_SHADOW } from "@website/builder/option_sequence";

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
            withSequence(BOX_BORDER_SHADOW, {
                OptionComponent: VerticalAlignmentOption,
                selector:".s_attributes_horizontal_col",
                applyTo: ":scope > .row",
                props: {
                    level: 0,
                    justify: false,
                },
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setVerticalAlignment: {
                ...classAction,
                getPriority: ({ params: { mainParam: classNames } = { mainParam: "" } }) =>
                    classNames === "align-items-stretch" ? 0 : 1,
                isApplied: (...args) => {
                    const {
                        params: { mainParam: classNames },
                    } = args[0];
                    if (classNames === "align-items-stretch") {
                        return true;
                    }
                    return classAction.isApplied(...args);
                },
            },
        };
    }
}
registry
    .category("website-plugins")
    .add(VerticalAlignmentOptionPlugin.id, VerticalAlignmentOptionPlugin);
