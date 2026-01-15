import { SelectNumberColumn } from "@html_builder/core/select_number_column";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { AddElementOption } from "./add_element_option";
import { SpacingOption } from "./spacing_option";

export class LayoutOption extends BaseOptionComponent {
    static template = "website.LayoutOption";
    static selector = "section, section.s_carousel_wrapper .carousel-item, .s_carousel_intro_item";
    static exclude =
        ".s_dynamic, .s_dynamic_snippet_content, .s_dynamic_snippet_title, .s_masonry_block, .s_framed_intro, .s_features_grid, .s_media_list, .s_table_of_content, .s_process_steps, .s_image_gallery, .s_pricelist_boxed, .s_quadrant, .s_pricelist_cafe, .s_faq_horizontal, .s_image_frame, .s_card_offset, .s_contact_info, .s_tabs, .s_tabs_images, .s_floating_blocks .s_floating_blocks_block, .s_banner_categories";
    static applyTo = ":scope > *:has(> .row), :scope > .s_allow_columns";
    static components = {
        SelectNumberColumn,
        SpacingOption,
        AddElementOption,
    };
}

export class LayoutGridOption extends BaseOptionComponent {
    static template = "website.LayoutGridOption";
    static selector =
        "section.s_masonry_block, section.s_quadrant, section.s_image_frame, section.s_card_offset, section.s_contact_info, section.s_framed_intro, section.s_banner_categories";
    static applyTo = ":scope > *:has(> .row)";
    static components = {
        SpacingOption,
        AddElementOption,
    };
}
