import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CardOption } from "./card_option";
import { CARD_PARENT_HANDLERS } from "@html_builder/website_builder/plugins/options/utils";
import { WebsiteBackgroundOption } from "./background_option";

class CardOptionPlugin extends Plugin {
    static id = "cardOption";
    resources = {
        builder_options: [
            {
                OptionComponent: CardOption,
                selector: ".s_card",
                exclude: `div:is(${CARD_PARENT_HANDLERS}) > .s_card`,
            },
            {
                OptionComponent: CardOption,
                selector: CARD_PARENT_HANDLERS,
                applyTo: ":scope > .s_card:not(.s_carousel_cards_card)",
                props: {
                    disableWidth: true,
                },
            },
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: CARD_PARENT_HANDLERS,
                applyTo: ":scope > .s_carousel_cards_card",
                props: {
                    withColors: true,
                    withImages: true,
                    withShapes: true,
                    withColorCombinations: true,
                    withGradient: true,
                },
            },
        ],
    };
}

registry.category("website-plugins").add(CardOptionPlugin.id, CardOptionPlugin);
