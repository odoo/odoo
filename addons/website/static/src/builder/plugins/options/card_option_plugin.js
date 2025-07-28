import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import {
    CARD_DISABLE_WIDTH_APPLY_TO,
    CARD_PARENT_HANDLERS,
    WEBSITE_BG_APPLY_TO,
} from "@website/builder/plugins/options/utils";
import { BaseWebsiteBackgroundOption } from "./background_option";
import { CarouselCardsItemOption } from "./carousel_cards_item_option";
import { CardOption, CardWithoutWidthOption } from "./card_option";

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

class CardOptionPlugin extends Plugin {
    static id = "cardOption";

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
    };
}

registry.category("website-plugins").add(CardOptionPlugin.id, CardOptionPlugin);
