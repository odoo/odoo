import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    CARD_DISABLE_WIDTH_APPLY_TO,
    CARD_EXCLUDE,
    CARD_PARENT_HANDLERS,
    CARD_SELECTOR,
    WEBSITE_BG_APPLY_TO,
} from "@website/builder/plugins/options/utils";
import { WebsiteBackgroundOption } from "./background_option";
import { CarouselCardsItemOption } from "./carousel_cards_item_option";

class CardOptionPlugin extends Plugin {
    static id = "cardOption";

    resources = {
        builder_options: [
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: CARD_PARENT_HANDLERS,
                applyTo: WEBSITE_BG_APPLY_TO,
                props: {
                    withColors: true,
                    withImages: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            },
            CarouselCardsItemOption,
        ],
        mark_color_level_selector_params: [
            { selector: CARD_SELECTOR, exclude: CARD_EXCLUDE },
            { selector: CARD_PARENT_HANDLERS, applyTo: CARD_DISABLE_WIDTH_APPLY_TO },
            { selector: CARD_PARENT_HANDLERS, applyTo: WEBSITE_BG_APPLY_TO },
        ],
    };
}

registry.category("website-plugins").add(CardOptionPlugin.id, CardOptionPlugin);
