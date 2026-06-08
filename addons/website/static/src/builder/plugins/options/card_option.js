import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useGetItemValue } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { CardImageOption } from "./card_image_option";
import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class CardOption extends BaseOptionComponent {
    static id = "card_option";
    static template = "website.CardOption";
    static components = {
        CardImageOption,
        WebsiteBackgroundOption,
    };
    props = props({
        disableWidth: t.boolean().optional(false),
    });
    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
    }
}

registry.category("website-options").add(CardOption.id, CardOption);
