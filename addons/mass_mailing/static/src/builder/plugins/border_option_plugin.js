import { before, VERTICAL_ALIGNMENT, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class BorderOptionPlugin extends Plugin {
    static id = "mass_mailing.BorderOption";
    resources = {
        builder_options: [
            withSequence(before(WIDTH), {
                template: "mass_mailing.BorderOption",
                selector:
                    ".s_three_columns .row > div, .s_comparisons .row > div, .s_mail_block_event .row > div",
                applyTo: ".card",
            }),
            withSequence(before(WIDTH), {
                template: "mass_mailing.BorderOption",
                selector: ".s_text_block",
            }),
            withSequence(before(WIDTH), {
                template: "mass_mailing.BorderOption",
                selector: ".o_mail_block_discount2",
                applyTo: "table",
            }),
            withSequence(VERTICAL_ALIGNMENT, {
                template: "mass_mailing.BorderOption",
                selector: ".row > div",
                exclude:
                    ".o_mail_wrapper_td, .s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_image_gallery .row > div",
            }),
        ],
    };
}

registry.category("mass_mailing-plugins").add(BorderOptionPlugin.id, BorderOptionPlugin);
