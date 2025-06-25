import { after, before, WIDTH } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

class HorizontalPaddingOptionPlugin extends Plugin {
    static id = "horizontalPaddingOption";
    selector = "[class*='col-lg-'], .s_discount2, .s_text_block, .s_media_list, .s_picture, .s_rating";
    resources = {
        mark_color_level_selector_params: [{ selector: this.selector }],
        builder_options: [
            withSequence(after(WIDTH)), {
                template: "mass_mailing.PaddingOption",
                selector: this.selector,
                exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
            },
        ],
    };
}
// TODO: as in master, the position of a background image does not work
// correctly.
registry.category("builder-plugins").add(HorizontalPaddingOptionPlugin.id, HorizontalPaddingOptionPlugin );
