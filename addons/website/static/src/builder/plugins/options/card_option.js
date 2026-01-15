import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { CardImageOption } from "./card_image_option";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { CARD_DISABLE_WIDTH_APPLY_TO, CARD_PARENT_HANDLERS } from "./utils";

export class BaseCardOption extends BaseOptionComponent {
    static template = "website.CardOption";
    static components = {
        CardImageOption,
        WebsiteBackgroundOption: BaseWebsiteBackgroundOption,
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
    static selector = ".s_card";
    static exclude = `div:is(${CARD_PARENT_HANDLERS}) > .s_card`;
}

export class CardWithoutWidthOption extends BaseCardOption {
    static selector = CARD_PARENT_HANDLERS;
    static applyTo = CARD_DISABLE_WIDTH_APPLY_TO;
    static defaultProps = {
        disableWidth: true,
    };
}
