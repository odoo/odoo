import { after, before, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { LayoutColumnOption } from "@html_builder/plugins/layout_column_option";

class GenericBlockOptionPlugin extends Plugin {
    static id = "GenericBlockOption";
    colorPickerSelector = `.note-editable .oe_structure > div:not(:has(> .o_mail_snippet_general)),
        .note-editable .oe_structure > div.o_mail_snippet_general,
        .note-editable .oe_structure > div.o_mail_snippet_general .o_cc,
        .s_mail_color_blocks_2 .row > div`;
    resources = {
        mark_color_level_selector_params: [{ selector: ".o_mail_snippet_general" }],
        builder_options: [
            withSequence(before(WIDTH), {
                OptionComponent: LayoutColumnOption,
                selector: ".o_mail_snippet_general",
                applyTo: "* > *:has(> .row:not(.s_nb_column_fixed)), * > .s_allow_columns"
            }),
            {
                template: "mass_mailing.BlockquoteOption",
                selector: ".o_mail_snippet_general",
                exclude: ".o_mail_snippet_general .row > div *"
            },
            {
                template: "mass_mailing.ColorPickerOption",
                selector: this.colorPickerSelector,
                exclude: ".o_mail_no_colorpicker, .o_mail_no_options, .s_mail_color_blocks_2"
            },
        ],
        so_snippet_addition_selector: [".o_mail_snippet_general"],
        so_content_addition_selector: [
            ".s_mail_blockquote, .s_mail_alert, .s_rating, .s_hr, .s_mail_text_highlight"
        ]
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("builder-plugins").add(GenericBlockOptionPlugin.id, GenericBlockOptionPlugin );
