import { CARD_PARENT_HANDLERS } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export const WEBSITE_BG_APPLY_TO = ":scope > .s_carousel_cards_card";
export const CARD_DISABLE_WIDTH_APPLY_TO = ":scope > .s_card:not(.s_carousel_cards_card)";

export class CardOptionPlugin extends Plugin {
    static id = "cardOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        content_editable_selectors: [
            ".s_card > *",
            ".s_card figure > img",
        ],
        content_not_editable_selectors: ".s_card figure",
        mark_color_level_selector_params: [
            { selector: ".s_card", exclude: `div:is(${CARD_PARENT_HANDLERS}) > .s_card` },
            { selector: CARD_PARENT_HANDLERS, applyTo: CARD_DISABLE_WIDTH_APPLY_TO },
            { selector: CARD_PARENT_HANDLERS, applyTo: WEBSITE_BG_APPLY_TO },
        ],
        builder_options_context: {
            cardDisableWidthApplyTo: CARD_DISABLE_WIDTH_APPLY_TO,
            websiteBgApplyTo: WEBSITE_BG_APPLY_TO,
            cardParentHandlers: CARD_PARENT_HANDLERS,
        },
    };
}

registry.category("website-plugins").add(CardOptionPlugin.id, CardOptionPlugin);
