import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { CardImageOption } from "./card_image_option";
import { registry } from "@web/core/registry";

export class BaseCardOption extends BaseOptionComponent {
    static id = "base_card_option";
    static template = "website.CardOption";
    static components = {
        CardImageOption,
        WebsiteBackgroundOption: BaseWebsiteBackgroundOption,
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

registry.category("builder-options").add(BaseCardOption.id, BaseCardOption);
