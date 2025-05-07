import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CARD_PARENT_HANDLERS, BASE_ONLY_BG_IMAGE_SELECTOR } from "./utils";
import { BLOCKQUOTE_PARENT_HANDLERS } from "@html_builder/core/utils";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_BEFORE } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";

export class WebsiteBackgroundCarouselOption extends BaseWebsiteBackgroundOption {
    static selector = "section";
    static applyTo = ":scope > .carousel:not(.s_carousel_cards)";
    static defaultProps = {
        withColors: true,
        withImages: true,
        withVideos: true,
        withShapes: true,
        withColorCombinations: true,
    };
}

export class WebsiteBackgroundBGColorImageOption extends BaseWebsiteBackgroundOption {
    static selector =
        "section, .carousel-item, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .parallax, .s_text_cover .row > .o_not_editable, .s_website_form_cover .row > .o_not_editable, .s_split_intro .row > .o_not_editable, .s_bento_grid .row > div, .s_banner_categories .row > div, .s_ecomm_categories_showcase_block, .s_bento_grid_avatars .row > div";
    static exclude = `${BASE_ONLY_BG_IMAGE_SELECTOR}, .s_carousel_wrapper, .s_image_gallery .carousel-item, .s_google_map, .s_map, [data-snippet] :not(.oe_structure) > [data-snippet], .s_masonry_block .s_col_no_resize, .s_quotes_carousel_wrapper, .s_carousel_intro_wrapper, .s_carousel_cards_item, .s_dynamic_snippet_category .s_dynamic_snippet_title`;
    static defaultProps = {
        withColors: true,
        withImages: true,
        withVideos: true,
        withShapes: true,
        withColorCombinations: true,
    };
}
export class WebsiteBackgroundBGColorOption extends BaseWebsiteBackgroundOption {
    static selector =
        "section .row > div, .s_text_highlight, .s_mega_menu_thumbnails_footer, .s_hr, .s_cta_badge";
    static exclude = `.s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .s_image_gallery .row > div, .s_text_cover .row > .o_not_editable, [data-snippet] :not(.oe_structure) > .s_hr, ${CARD_PARENT_HANDLERS}, .s_website_form_cover .row > .o_not_editable, .s_bento_grid .row > div, .s_banner_categories .row > div, ${BLOCKQUOTE_PARENT_HANDLERS}, .s_bento_grid_avatars .row > div`;
    static defaultProps = {
        withColors: true,
        withImages: false,
        withColorCombinations: true,
    };
}

export class WebsiteBackgroundOnlyBGImageOption extends BaseWebsiteBackgroundOption {
    static selector = BASE_ONLY_BG_IMAGE_SELECTOR;
    static exclude = "";
    static defaultProps = {
        withColors: false,
        withImages: true,
        withVideos: true,
        withShapes: true,
        withColorCombinations: false,
    };
}

class WebsiteBackgroundOptionPlugin extends Plugin {
    static id = "websiteOption";
    carouselApplyTo = ":scope > .carousel:not(.s_carousel_cards)";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_BEFORE, WebsiteBackgroundCarouselOption),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, WebsiteBackgroundBGColorImageOption),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, WebsiteBackgroundBGColorOption),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, WebsiteBackgroundOnlyBGImageOption),
        ],
        mark_color_level_selector_params: [
            {
                selector: WebsiteBackgroundCarouselOption.selector,
                applyTo: WebsiteBackgroundCarouselOption.applyTo,
            },
            {
                selector: WebsiteBackgroundBGColorImageOption.selector,
                exclude: WebsiteBackgroundBGColorImageOption.exclude,
            },
            {
                selector: WebsiteBackgroundBGColorOption.selector,
                exclude: WebsiteBackgroundBGColorOption.exclude,
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteBackgroundOptionPlugin.id, WebsiteBackgroundOptionPlugin);
