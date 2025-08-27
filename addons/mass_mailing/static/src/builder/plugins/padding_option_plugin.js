import { after, VERTICAL_ALIGNMENT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class PaddingOptionPlugin extends Plugin {
    static id = "horizontalPaddingOption";
    selector =
        "[class*='col-md-'], .s_discount2, .s_text_block, .s_media_list, .s_picture, .s_rating, .s_title, .o_mail_block_footer_social, .s_header_logo, .s_header_social";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            withSequence(after(VERTICAL_ALIGNMENT), {
                template: "mass_mailing.HorizontalPaddingOption",
                selector: this.selector,
                exclude: ".s_col_no_resize.row > div, .s_col_no_resize, img",
            }),
            withSequence(after(VERTICAL_ALIGNMENT), {
                template: "mass_mailing.VerticalPaddingOption",
                selector: ".o_mail_block_footer_social, .s_header_logo, .s_header_social",
                exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
            }),
        ],
    };
}

registry.category("mass_mailing-plugins").add(PaddingOptionPlugin.id, PaddingOptionPlugin);
