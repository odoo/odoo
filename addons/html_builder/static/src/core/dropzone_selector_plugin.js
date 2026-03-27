import { Plugin } from "@html_editor/plugin";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {CSSSelector[]} so_content_addition_selector
 * @typedef {CSSSelector[]} so_snippet_addition_selector
 */

const card_parent_handlers =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div, .s_newsletter_centered .row > div, .s_company_team_spotlight .row > div, .s_comparisons_horizontal .row > div, .s_company_team_grid .row > div, .s_company_team_card .row > div, .s_carousel_cards_item";
const special_cards_selector = `.s_card.s_timeline_card, div:is(${card_parent_handlers}) > .s_card`;

const so_snippet_addition_drop_in =
    ":not(p).oe_structure:not(.oe_structure_solo), :not(.o_mega_menu):not(p)[data-oe-type=html], :not(p).oe_structure.oe_structure_solo:not(:has(> section:not(.s_snippet_group), > div:not(.o_hook_drop_zone)))";

// TODO need to split by addons

export class DropZoneSelectorPlugin extends Plugin {
    static id = "dropzone_selector";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        dropzone_selector: [
            {
                selector: ".accordion > .accordion-item",
                dropIn: ".accordion:has(> .accordion-item)",
            },
            {
                plugin: this,
                get selector() {
                    return this.plugin.getResource("so_snippet_addition_selector").join(", ");
                },
                dropIn: so_snippet_addition_drop_in,
            },
            {
                plugin: this,
                get selector() {
                    return [
                        ...this.plugin.getResource("so_content_addition_selector"),
                        ".s_card",
                    ].join(", ");
                },
                exclude: `${special_cards_selector}`,
                dropIn: "nav, .row.o_grid_mode",
                get dropNear() {
                    return `p, h1, h2, h3, ul, ol, div:not(.o_grid_item_image) > img, div:not(.o_grid_item_image) > a, .btn, ${this.plugin
                        .getResource("so_content_addition_selector")
                        .join(", ")}, .s_card:not(${special_cards_selector})`;
                },
                excludeNearParent: so_snippet_addition_drop_in,
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
        ],
        so_snippet_addition_selector: ["section", ".parallax", ".s_hr"],
        so_content_addition_selector: [
            "blockquote",
            ".s_text_highlight",
            ".s_donation", // TODO: move to plugin
            ".o_snippet_drop_in_only",
        ],
    };
}
