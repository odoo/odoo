import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { selectElements } from "@html_editor/utils/dom_traversal";
import {
    CARD_DISABLE_WIDTH_APPLY_TO,
    CARD_PARENT_HANDLERS,
    CARD_PARENT_HANDLERS_ARRAY,
    WEBSITE_BG_APPLY_TO,
} from "@website/builder/plugins/options/utils";
import { BaseWebsiteBackgroundOption } from "./background_option";
import { CarouselCardsItemOption } from "./carousel_cards_item_option";
import { CardOption, CardWithoutWidthOption } from "./card_option";

const toNonGridRowSelector = (selector) =>
    `${selector.replace(".row", ".row:not(.o_grid_mode)")}:has(> ${CardOption.selector})`;

export class WebsiteBackgroundCardOption extends BaseWebsiteBackgroundOption {
    static selector = CARD_PARENT_HANDLERS;
    static applyTo = WEBSITE_BG_APPLY_TO;
    static defaultProps = {
        withColors: true,
        withImages: true,
        withShapes: true,
        withColorCombinations: true,
    };
}

export class CardOptionPlugin extends Plugin {
    static id = "cardOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [
            CardOption,
            CardWithoutWidthOption,
            WebsiteBackgroundCardOption,
            CarouselCardsItemOption,
        ],
        mark_color_level_selector_params: [
            { selector: CardOption.selector, exclude: CardOption.exclude },
            { selector: CARD_PARENT_HANDLERS, applyTo: CARD_DISABLE_WIDTH_APPLY_TO },
            { selector: CARD_PARENT_HANDLERS, applyTo: WEBSITE_BG_APPLY_TO },
        ],
        content_editable_selectors: [
            `${CardOption.selector} > *`,
            `${CardOption.selector} figure > img`,
        ],
        content_not_editable_selectors: `${CardOption.selector} figure`,
        content_not_editable_providers: (rootEl) => {
            const rowSelector = CARD_PARENT_HANDLERS_ARRAY.map(toNonGridRowSelector);
            return [...selectElements(rootEl, rowSelector)];
        },
        selection_blocker_row_enablers: (blockerRowCandidate) => {
            if (blockerRowCandidate.nodeType !== Node.ELEMENT_NODE) {
                return;
            }
            for (const rowDivEl of blockerRowCandidate.querySelectorAll(":scope > div")) {
                const rowSelector = CARD_PARENT_HANDLERS_ARRAY.map(toNonGridRowSelector);
                if (rowDivEl.matches(rowSelector)) {
                    return true;
                }
            }
        },
    };
}

registry.category("website-plugins").add(CardOptionPlugin.id, CardOptionPlugin);
