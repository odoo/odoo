import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class PriceListCafeDescriptionOption extends BaseOptionComponent {
    static id = "price_list_cafe_description_option";
    static template = "website.PriceListCafeDescriptionOption";
    static components = { WebsiteBorderConfigurator };
}

registry
    .category("website-options")
    .add(PriceListCafeDescriptionOption.id, PriceListCafeDescriptionOption);
