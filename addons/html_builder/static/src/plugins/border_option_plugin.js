import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { card_parent_handlers } from "./card_option";

class BorderOptionPlugin extends Plugin {
    static id = "borderOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.BorderOption",
                selector: "section .row > div",
                exclude: `.s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_image_gallery .row > div, .s_masonry_block .s_col_no_resize, .s_text_cover .row > .o_not_editable, ${card_parent_handlers}`,
            },
        ],
    };
}
registry.category("website-plugins").add(BorderOptionPlugin.id, BorderOptionPlugin);
