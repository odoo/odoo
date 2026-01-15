import { BaseOptionComponent } from "@html_builder/core/utils";
import { after, VERTICAL_ALIGNMENT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

export class HorizontalPaddingOption extends BaseOptionComponent {
    static template = "mass_mailing.HorizontalPaddingOption";
    static selector =
        "[class*='col-md-'], .s_discount2, .s_text_block, .s_media_list, .s_picture, .s_rating, .s_title, .o_mail_block_footer_social, .s_header_logo, .s_header_social";
    static exclude = ".s_col_no_resize.row > div, .s_col_no_resize, img";
}

export class VerticalPaddingOption extends BaseOptionComponent {
    static template = "mass_mailing.VerticalPaddingOption";
    static selector = ".o_mail_block_footer_social, .s_header_logo, .s_header_social";
    static exclude = ".s_col_no_resize.row > div, .s_col_no_resize";
}

class PaddingOptionPlugin extends Plugin {
    static id = "horizontalPaddingOption";
    selector = HorizontalPaddingOption.selector;
    resources = {
        mark_color_level_selector_params: [{ selector: HorizontalPaddingOption.selector }],
        builder_options: [
            withSequence(after(VERTICAL_ALIGNMENT), HorizontalPaddingOption),
            withSequence(after(VERTICAL_ALIGNMENT), VerticalPaddingOption),
        ],
    };
}

registry.category("mass_mailing-plugins").add(PaddingOptionPlugin.id, PaddingOptionPlugin);
