import { Plugin } from "@html_editor/plugin";
import { CARD_PARENT_HANDLERS } from "./utils";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {CSSSelector[]} so_content_addition_selectors
 * @typedef {CSSSelector[]} so_snippet_addition_selectors
 */

const special_cards_selector = `.s_card.s_timeline_card, div:is(${CARD_PARENT_HANDLERS}) > .s_card`;

const so_snippet_addition_drop_in =
    ":not(p).oe_structure:not(.oe_structure_solo), :not(.o_mega_menu):not(p)[data-oe-type=html], :not(p).oe_structure.oe_structure_solo:not(:has(> section:not(.s_snippet_group), > div:not(.o_hook_drop_zone)))";

// TODO need to split by addons

export class DropZoneSelectorPlugin extends Plugin {
    static id = "dropzone_selectors";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        dropzone_selectors: [
            {
                selector: ".accordion > .accordion-item",
                dropIn: ".accordion:has(> .accordion-item)",
            },
            {
                plugin: this,
                get selector() {
                    return this.plugin.getResource("so_snippet_addition_selectors").join(", ");
                },
                dropIn: so_snippet_addition_drop_in,
            },
            {
                plugin: this,
                get selector() {
                    return [
                        ...this.plugin.getResource("so_content_addition_selectors"),
                        ".s_card",
                    ].join(", ");
                },
                exclude: `${special_cards_selector}`,
                dropIn: "nav, .row.o_grid_mode",
                get dropNear() {
                    return `p, h1, h2, h3, ul, ol, div:not(.o_grid_item_image) > img, div:not(.o_grid_item_image) > a, .btn, ${this.plugin
                        .getResource("so_content_addition_selectors")
                        .join(", ")}, .s_card:not(${special_cards_selector})`;
                },
                excludeNearParent: so_snippet_addition_drop_in,
                excludeAncestor: ".s_image_gallery",
            },
            {
                selector: ".row > div",
                exclude:
                    ".s_col_no_resize.row > div, .s_col_no_resize, .s_image_gallery .row > div",
                dropNear: ".row:not(.s_col_no_resize) > div, .row.o_grid_mode > div",
                excludeAncestor: ".s_image_gallery",
            },
        ],
        so_snippet_addition_selectors: ["section", ".parallax", ".s_hr"],
        so_content_addition_selectors: [
            "blockquote",
            ".s_text_highlight",
            ".s_donation", // TODO: move to plugin
            ".o_snippet_drop_in_only",
        ],
    };
}
