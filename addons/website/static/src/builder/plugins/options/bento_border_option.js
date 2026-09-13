import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class BentoBorderOption extends BaseOptionComponent {
    static id = "bento_border_option";
    static template = "website.BentoBorderOption";
    static components = {
        WebsiteBorderConfigurator,
    };
}

registry.category("website-options").add(BentoBorderOption.id, BentoBorderOption);
