import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class FloatingBlocksBlockOption extends BaseOptionComponent {
    static id = "floating_blocks_block_option";
    static template = "website.FloatingBlocksBlockOption";
    static components = { WebsiteBorderConfigurator };
}

registry.category("website-options").add(FloatingBlocksBlockOption.id, FloatingBlocksBlockOption);
