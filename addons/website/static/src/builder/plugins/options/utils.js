export const CARD_PARENT_HANDLERS =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div, .s_newsletter_centered .row > div, .s_company_team_spotlight .row > div, .s_comparisons_horizontal .row > div, .s_company_team_grid .row > div, .s_company_team_card .row > div, .s_carousel_cards_item";
export const SPECIAL_CARD_SELECTOR = `div:is(${CARD_PARENT_HANDLERS}) > .s_card`;

export const BASE_ONLY_BG_IMAGE_SELECTOR = "footer .oe_structure > *:not(.o_footer_bottom_part)";

export const CARD_DISABLE_WIDTH_APPLY_TO = ":scope > .s_card:not(.s_carousel_cards_card)";
export const WEBSITE_BG_APPLY_TO = ":scope > .s_carousel_cards_card";
