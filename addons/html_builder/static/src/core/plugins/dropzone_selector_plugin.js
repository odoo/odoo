import { Plugin } from "@html_editor/plugin";

// TODO s_website_form, s_searchbar_input were added by extending xpath.
const so_content_addition_selector = `blockquote, .s_alert, .o_facebook_page, .s_share, .s_social_media, .s_rating, .s_hr, .s_google_map, .s_map, .s_countdown, .s_chart, .s_text_highlight, .s_progress_bar, .s_badge, .s_embed_code, .s_donation, .s_add_to_cart, .s_online_appointment, .o_snippet_drop_in_only, .s_image, .s_cta_badge, .s_accordion, .s_searchbar_input, .s_website_form`;
const card_parent_handlers =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div";
const special_cards_selector = `.s_card.s_timeline_card, div:is(${card_parent_handlers}) > .s_card`;

// TODO need to split by addons

export class DropZoneSelectorPlugin extends Plugin {
    static id = "dropzone_selector";
    resources = {
        dropzone_selector: [
            {
                selector: ".accordion > .accordion-item",
                dropIn: ".accordion:has(> .accordion-item)",
            },
            {
                selector: "section, .parallax, .s_hr", // TODO check extend so_snippet_addition_selector
                dropIn: ":not(p).oe_structure:not(.oe_structure_solo), :not(.o_mega_menu):not(p)[data-oe-type=html], :not(p).oe_structure.oe_structure_solo:not(:has(> section:not(.s_snippet_group), > div:not(.o_hook_drop_zone)))",
            },
            {
                selector: `${so_content_addition_selector}, .s_card`, // TODO check extend so_content_addition_selector
                exclude: `${special_cards_selector}`,
                dropNear: `p, h1, h2, h3, ul, ol, div:not(.o_grid_item_image) > img, div:not(.o_grid_item_image) > a, .btn, ${so_content_addition_selector}, .s_card:not(${special_cards_selector})`,
                dropIn: "nav",
                excludeNearParent:
                    ":not(p).oe_structure:not(.oe_structure_solo), :not(.o_mega_menu):not(p)[data-oe-type=html], :not(p).oe_structure.oe_structure_solo:not(:has(> section:not(.s_snippet_group), > div:not(.o_hook_drop_zone)))", // TODO not duplicate
            },
            {
                selector: ".o_mega_menu .nav > .nav-link",
                dropIn: ".o_mega_menu nav",
                dropNear: ".o_mega_menu .nav-link",
            },
            {
                selector: ".s_popup",
                exclude: "#website_cookies_bar",
                dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
            },
            {
                selector: ".s_website_form_field",
                exclude: ".s_website_form_dnone",
                dropNear: ".s_website_form_field",
                //TODO DROP LOCK WITHIN drop-lock-within="form"
            },
            {
                selector: ".row > div",
                exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
                dropNear: ".row:not(.s_col_no_resize) > div",
            },
            {
                selector: ".row > div",
                exclude: ".s_col_no_resize.row > div, .s_col_no_resize",
                dropNear: ".row.o_grid_mode > div",
            },
            {
                selector: ".s_group",
                dropNear: "p, h1, h2, h3, blockquote, .card",
            },
            {
                // TODO Move to website_massmailing
                selector: ".js_subscribe",
                dropNear: "p, h1, h2, h3, blockquote, .card",
            },
        ],
    };
}

/** TODO add xpath
 * <xpath expr:"//div[@id='so_content_addition']" position="attributes">
    <attribute name="selector" add=".s_progress_bar" separator:","/>
    <attribute name="dropNear" add=".s_progress_bar" separator:","/>
</xpath>
 */
