import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class BorderOption extends BaseOptionComponent {
    static id = "border_option";
    static template = "website.BorderOption";
    static components = {
        WebsiteBorderConfigurator,
    };
}

registry.category("website-options").add(BorderOption.id, BorderOption);
