import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const HORIZONTAL_PADDING_OPTION_SELECTOR = "[class*='col-md-'], .s_discount2, .s_text_block, .s_media_list, .s_picture, .s_rating, .s_title, .o_mail_block_footer_social, .s_header_logo, .s_header_social";
export class PaddingOptionPlugin extends Plugin {
    static id = "horizontalPaddingOption";

    resources = {
        mark_color_level_selector_params: [{ selector: HORIZONTAL_PADDING_OPTION_SELECTOR }],
        builder_options_context: {
            horizontalPaddingOptionSelector : HORIZONTAL_PADDING_OPTION_SELECTOR,
        }
    };
}

registry.category("mass_mailing-plugins").add(PaddingOptionPlugin.id, PaddingOptionPlugin);
