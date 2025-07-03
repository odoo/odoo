import { CARD_PARENT_HANDLERS } from "@website/builder/plugins/options/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BOX_BORDER_SHADOW } from "@website/builder/option_sequence";

class BorderOptionPlugin extends Plugin {
    static id = "borderOption";
    resources = {
        builder_options: [
            withSequence(BOX_BORDER_SHADOW, {
                template: "website.BorderOption",
                selector: "section .row > div, section:has(.s_carousel_cards)",
                exclude: `.s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_image_gallery .row > div, .s_masonry_block .s_col_no_resize, .s_text_cover .row > .o_not_editable, ${CARD_PARENT_HANDLERS}`,
            }),
        ],
    };
}
registry.category("website-plugins").add(BorderOptionPlugin.id, BorderOptionPlugin);
