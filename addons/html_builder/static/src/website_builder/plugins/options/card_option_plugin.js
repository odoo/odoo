import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { CardOption } from "./card_option";
import { CARD_PARENT_HANDLERS } from "@html_builder/website_builder/plugins/options/utils";
import { WebsiteBackgroundOption } from "./background_option";

class CardOptionPlugin extends Plugin {
    static id = "cardOption";
    cardSelector = ".s_card";
    cardExclude = `div:is(${CARD_PARENT_HANDLERS}) > .s_card`;
    cardDisableWidthApplyTo = ":scope > .s_card:not(.s_carousel_cards_card)";
    websiteBgApplyTo = ":scope > .s_carousel_cards_card";
    resources = {
        builder_options: [
            {
                OptionComponent: CardOption,
                selector: this.cardSelector,
                exclude: this.cardExclude,
            },
            {
                OptionComponent: CardOption,
                selector: CARD_PARENT_HANDLERS,
                applyTo: this.cardDisableWidthApplyTo,
                props: {
                    disableWidth: true,
                },
            },
            {
                OptionComponent: WebsiteBackgroundOption,
                selector: CARD_PARENT_HANDLERS,
                applyTo: this.websiteBgApplyTo,
                props: {
                    withColors: true,
                    withImages: true,
                    withShapes: true,
                    withColorCombinations: true,
                },
            },
        ],
        mark_color_level_selector_params: [
            { selector: this.cardSelector, exclude: this.cardExclude },
            { selector: CARD_PARENT_HANDLERS, applyTo: this.cardDisableWidthApplyTo },
            { selector: CARD_PARENT_HANDLERS, applyTo: this.websiteBgApplyTo },
        ],
    };
}

registry.category("website-plugins").add(CardOptionPlugin.id, CardOptionPlugin);
