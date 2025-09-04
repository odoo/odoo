import { before, VERTICAL_ALIGNMENT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class ColorPickerOptionPlugin extends Plugin {
    static id = "mass_mailing.ColorPicker";
    colorPickerSelector = `.note-editable .oe_structure > div:not(:has(> .o_mail_snippet_general)),
        .note-editable .oe_structure > .o_mail_snippet_general,
        .note-editable .oe_structure > .o_mail_snippet_general .o_cc,
        .s_mail_color_blocks_2 .row > div`;

    resources = {
        builder_options: [
            withSequence(before(VERTICAL_ALIGNMENT), {
                // Generic option
                template: "mass_mailing.ColorPickerOption",
                selector: this.colorPickerSelector,
                exclude: ".o_mail_no_colorpicker, .o_mail_no_options, .s_mail_color_blocks_2",
            }),
            {
                template: "mass_mailing.ColorPickerOption",
                selector:
                    ".s_three_columns .row > div, .s_comparisons .row > div, .s_mail_block_event .row > div",
                applyTo: ".card-body",
            },
        ],
    };
}

registry.category("mass_mailing-plugins").add(ColorPickerOptionPlugin.id, ColorPickerOptionPlugin);
