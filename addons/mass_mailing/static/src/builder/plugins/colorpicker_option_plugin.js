import { BaseOptionComponent } from "@html_builder/core/utils";
import { before, VERTICAL_ALIGNMENT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class ColorPickerOption extends BaseOptionComponent {
    static template = "mass_mailing.ColorPickerOption";
    // This selector targets all direct children of .oe_structure except nested structures
    static selector = `.note-editable .oe_structure > div:not(:has(> .o_mail_snippet_general)),
        .note-editable .oe_structure > .o_mail_snippet_general,
        .note-editable .oe_structure > .o_mail_snippet_general .o_cc,
        .s_mail_color_blocks_2 .row > div, table td, .s_cta_badge`;
    static exclude = ".o_mail_no_colorpicker, .o_mail_no_options, .s_mail_color_blocks_2";
}

export class ColorPickerOption2 extends BaseOptionComponent {
    static template = "mass_mailing.ColorPickerOption";
    static selector =
        ".s_three_columns .row > div, .s_comparisons .row > div, .s_mail_block_event .row > div";
    static applyTo = ".card-body, .card-footer";
}

class ColorPickerOptionPlugin extends Plugin {
    static id = "mass_mailing.ColorPicker";
    colorPickerSelector = ColorPickerOption.selector;

    resources = {
        builder_options: [
            withSequence(before(VERTICAL_ALIGNMENT), ColorPickerOption),
            ColorPickerOption2,
        ],
    };
}

registry.category("mass_mailing-plugins").add(ColorPickerOptionPlugin.id, ColorPickerOptionPlugin);
