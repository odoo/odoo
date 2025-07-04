import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BorderOptionPlugin extends Plugin {
    static id = "mass_mailing.BorderOption";
    resources = {
        builder_options: [
            {
                template: "mass_mailing.BorderOptionNoRoundedCornersDependency",
                selector: ".s_three_columns .row > div, .s_comparisons .row > div, .s_mail_block_event .row > div",
                applyTo: ".card",
            },
            {
                template: "mass_mailing.BorderOption",
                selector: ".o_mail_block_discount2",
                applyTo: "table",
            },
            {
                template: "mass_mailing.BorderOption",
                selector: ".row > div",
                exclude: ".o_mail_wrapper_td, .s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_image_gallery .row > div",
            }
        ],
    }
}

registry.category("mass_mailing-plugins").add(BorderOptionPlugin.id, BorderOptionPlugin);
