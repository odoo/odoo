import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@html_builder/website_builder/plugins/options/background_option";
import { CardImageOption } from "./card_image_option";

export class CardOption extends BaseOptionComponent {
    static template = "website.CardOption";
    static components = { CardImageOption, WebsiteBackgroundOption };
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
