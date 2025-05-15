import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { CardImageOption } from "./card_image_option";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export class CardOption extends BaseOptionComponent {
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
