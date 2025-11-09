export const CARD_PARENT_HANDLERS =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div, .s_newsletter_centered .row > div, .s_company_team_spotlight .row > div, .s_comparisons_horizontal .row > div, .s_company_team_grid .row > div, .s_company_team_card .row > div, .s_carousel_cards_item";

// To remove in master, move it on the Option
export const ONLY_BG_COLOR_SELECTOR =
    "section .row > div, .s_text_highlight, .s_mega_menu_thumbnails_footer, .s_hr, .s_cta_badge";
export const ONLY_BG_COLOR_EXCLUDE = `.s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .s_image_gallery .row > div, .s_text_cover .row > .o_not_editable, [data-snippet] :not(.oe_structure) > .s_hr, ${CARD_PARENT_HANDLERS}, .s_website_form_cover .row > .o_not_editable, .s_bento_grid .row > div, .s_banner_categories .row > div`;

export const BASE_ONLY_BG_IMAGE_SELECTOR =
    ".s_tabs .oe_structure > *, footer .oe_structure > *:not(.o_footer_bottom_part)";
export const ONLY_BG_IMAGE_SELECTOR = BASE_ONLY_BG_IMAGE_SELECTOR;
export const ONLY_BG_IMAGE_EXCLUDE = "";

export const BOTH_BG_COLOR_IMAGE_SELECTOR =
    "section, .carousel-item, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .parallax, .s_text_cover .row > .o_not_editable, .s_website_form_cover .row > .o_not_editable, .s_split_intro .row > .o_not_editable, .s_bento_grid .row > div, .s_banner_categories .row > div, .s_ecomm_categories_showcase_block";
export const BOTH_BG_COLOR_IMAGE_EXCLUDE = `${BASE_ONLY_BG_IMAGE_SELECTOR}, .s_carousel_wrapper, .s_image_gallery .carousel-item, .s_google_map, .s_map, [data-snippet] :not(.oe_structure) > [data-snippet], .s_masonry_block .s_col_no_resize, .s_quotes_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_item, .s_dynamic_snippet_category .s_dynamic_snippet_title`;

export const CARD_DISABLE_WIDTH_APPLY_TO = ":scope > .s_card:not(.s_carousel_cards_card)";
export const WEBSITE_BG_APPLY_TO = ":scope > .s_carousel_cards_card";
