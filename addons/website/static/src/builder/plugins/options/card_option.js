import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { CardImageOption } from "./card_image_option";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import {
    CARD_DISABLE_WIDTH_APPLY_TO,
    CARD_EXCLUDE,
    CARD_PARENT_HANDLERS,
    CARD_SELECTOR,
} from "./utils";

export class BaseCardOption extends BaseOptionComponent {
    static template = "website.CardOption";
    static components = {
        CardImageOption,
        WebsiteBackgroundOption,
        BorderConfigurator,
        ShadowOption,
    };
    static props = {
        disableWidth: { type: Boolean, optional: true },
    };
    static defaultProps = {
        disableWidth: false,
    };
    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
    }
}
export class CardOption extends BaseCardOption {
    static selector = CARD_SELECTOR;
    static exclude = CARD_EXCLUDE;
}

export class CardWithoutWidthOption extends BaseCardOption {
    static selector = CARD_PARENT_HANDLERS;
    static applyTo = CARD_DISABLE_WIDTH_APPLY_TO;
    static defaultProps = {
        disableWidth: true,
    };
}
