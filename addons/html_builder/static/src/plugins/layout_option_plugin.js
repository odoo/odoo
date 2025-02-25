import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { LayoutOption } from "./layout_option";

class LayoutOptionPlugin extends Plugin {
    static id = "layoutOption";
    resources = {
        builder_options: {
            OptionComponent: LayoutOption,
            selector:
                ":is(section, section.s_carousel_wrapper .carousel-item, .s_carousel_intro_item):has(> * > .row, > .s_allow_columns)",
            exclude:
                ".s_dynamic, .s_dynamic_snippet_content, .s_dynamic_snippet_title, .s_masonry_block, .s_framed_intro, .s_features_grid, .s_media_list, .s_table_of_content, .s_process_steps, .s_image_gallery, .s_timeline, .s_pricelist_boxed, .s_quadrant, .s_pricelist_cafe, .s_faq_horizontal, .s_image_frame, .s_card_offset, .s_contact_info, .s_tabs",
        },
    };
}
registry.category("website-plugins").add(LayoutOptionPlugin.id, LayoutOptionPlugin);
