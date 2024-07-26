/** @odoo-module **/
import { registry } from "@web/core/registry";


export function registerOption(name, def, options) {
    if (!def.module) {
        def.module = "web_editor";
    }
    return registry.category("snippet_options").add(name, def, options);
}

export const SNIPPET_ADDITION_OPTION_ID = "so_snippet_addition";
export const CONTENT_ADDITION_OPTION_ID = "so_content_addition";

/**
 * Register a selector for generic snippet dropIn.
 *
 * @param {string} selector The selector to add.
 */
export function registerSnippetAdditionSelector(selector) {
    registry.category("snippet_options").get(SNIPPET_ADDITION_OPTION_ID).addSelector(selector);
}

/**
 * Register a selector for generic inner content drop.
 * This also adds the selector as a dropNear target for other inner content.
 *
 * @param {string} selector The selector to add.
 */
export function registerContentAdditionSelector(selector) {
    registry.category("snippet_options").get(CONTENT_ADDITION_OPTION_ID).addSelector(selector);
}


// TODO: @owl-options - some selectors should be defined in there respective
//  snippet options js file
const snippetAdditionSelectors = [
    "section",
    ".parallax",
    ".s_hr"
];
registerOption(SNIPPET_ADDITION_OPTION_ID, {
    _selector: snippetAdditionSelectors.join(", "),
    get selector() {
        return this._selector;
    },
    dropIn: ":not(p).oe_structure:not(.oe_structure_solo), :not(.o_mega_menu):not(p)[data-oe-type=html], :not(p).oe_structure.oe_structure_solo:not(:has(> section:not(.s_snippet_group), > div:not(.o_hook_drop_zone)))",

    addSelector(selector) {
        this._selector = this._selector + ", " + selector;
    },
});

// TODO: @owl-options - some selectors should be defined in there respective
//  snippet options js file
const contentAdditionSelectors = [
    "blockquote",
    ".s_card:not(.s_timeline_card)",
    ".s_alert",
    ".o_facebook_page",
    ".s_share",
    ".s_social_media",
    ".s_rating",
    ".s_hr",
    ".s_google_map",
    ".s_map",
    ".s_countdown",
    ".s_chart",
    ".s_text_highlight",
    ".s_progress_bar",
    ".s_badge",
    ".s_embed_code",
    ".s_donation",
    ".s_add_to_cart",
    ".s_online_appointment",
    ".o_snippet_drop_in_only",
    ".s_image"
];
registerOption(CONTENT_ADDITION_OPTION_ID, {
    _selector: contentAdditionSelectors.join(", "),
    get selector() {
        return this._selector;
    },
    get dropNear() {
        return "p, h1, h2, h3, ul, ol, div:not(.o_grid_item_image) > img, .btn, " + this._selector;
    },
    dropIn: "nav",

    addSelector(selector) {
        this._selector = this._selector + ", " + selector;
    },
});
