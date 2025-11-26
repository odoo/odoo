import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BLOCKQUOTE_PARENT_HANDLERS, CARD_PARENT_HANDLERS } from "@html_builder/core/utils";

export const BASE_ONLY_BG_IMAGE_SELECTOR = "footer .oe_structure > *:not(.o_footer_bottom_part)";
export const WEBSITE_BACKGROUND_BG_COLOR_IMAGE_OPTION_SELECTOR =
    "section, .carousel-item, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .parallax, .s_text_cover .row > .o_not_editable, .s_website_form_cover .row > .o_not_editable, .s_split_intro .row > .o_not_editable, .s_bento_grid .row > div, .s_banner_categories .row > div, .s_ecomm_categories_showcase_block, .s_bento_grid_avatars .row > div";
export const WEBSITE_BACKGROUND_BG_COLOR_IMAGE_OPTION_EXCLUDE = `${BASE_ONLY_BG_IMAGE_SELECTOR}, .s_carousel_wrapper, .s_image_gallery .carousel-item, .s_google_map, .s_map, [data-snippet] :not(.oe_structure) > [data-snippet], .s_masonry_block .s_col_no_resize, .s_quotes_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_item, .s_dynamic_snippet_category .s_dynamic_snippet_title`;
export const WEBSITE_BACKGROUND_BG_COLOR_OPTION_SELECTOR =
    "section .row > div, .s_text_highlight, .s_mega_menu_thumbnails_footer, .s_hr, .s_cta_badge";
export const WEBSITE_BACKGROUND_BG_COLOR_OPTION_EXCLUDE = `.s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .s_image_gallery .row > div, .s_text_cover .row > .o_not_editable, [data-snippet] :not(.oe_structure) > .s_hr, ${CARD_PARENT_HANDLERS}, .s_website_form_cover .row > .o_not_editable, .s_bento_grid .row > div, .s_banner_categories .row > div, ${BLOCKQUOTE_PARENT_HANDLERS}, .s_bento_grid_avatars .row > div`;

export class WebsiteBackgroundOptionPlugin extends Plugin {
    static id = "websiteOption";
    carouselApplyTo = ":scope > .carousel:not(.s_carousel_cards)";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_color_level_selector_params: [
            {
                selector: "section",
                applyTo: ":scope > .carousel:not(.s_carousel_cards)",
            },
            {
                selector: WEBSITE_BACKGROUND_BG_COLOR_IMAGE_OPTION_SELECTOR,
                exclude: WEBSITE_BACKGROUND_BG_COLOR_IMAGE_OPTION_EXCLUDE,
            },
            {
                selector: WEBSITE_BACKGROUND_BG_COLOR_OPTION_SELECTOR,
                exclude: WEBSITE_BACKGROUND_BG_COLOR_OPTION_EXCLUDE,
            },
        ],
        builder_options_context: {
            baseOnlyBgImageSelector: BASE_ONLY_BG_IMAGE_SELECTOR,
            websiteBackgroundBgColorImageOptionSelector:
                WEBSITE_BACKGROUND_BG_COLOR_IMAGE_OPTION_SELECTOR,
            websiteBackgroundBgColorImageOptionExclude:
                WEBSITE_BACKGROUND_BG_COLOR_IMAGE_OPTION_EXCLUDE,
            websiteBackgroundBgColorOptionSelector: WEBSITE_BACKGROUND_BG_COLOR_OPTION_SELECTOR,
            websiteBackgroundBgColorOptionExclude: WEBSITE_BACKGROUND_BG_COLOR_OPTION_EXCLUDE,
        },
    };
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundOptionPlugin.id, WebsiteBackgroundOptionPlugin);
