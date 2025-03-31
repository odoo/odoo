import { CARD_PARENT_HANDLERS } from "@html_builder/website_builder/plugins/options/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BorderOptionPlugin extends Plugin {
    static id = "borderOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.BorderOption",
                selector: "section .row > div",
                exclude: `.s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_image_gallery .row > div, .s_masonry_block .s_col_no_resize, .s_text_cover .row > .o_not_editable, ${CARD_PARENT_HANDLERS}`,
            },
        ],
    };
}
registry.category("website-plugins").add(BorderOptionPlugin.id, BorderOptionPlugin);
