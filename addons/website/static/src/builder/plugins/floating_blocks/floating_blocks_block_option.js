import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { AddElementOption } from "@website/builder/plugins/layout_option/add_element_option";

export class FloatingBlocksBlockOption extends BaseOptionComponent {
    static template = "website.FloatingBlocksBlockOption";
    static components = {
        BorderConfigurator,
        AddElementOption,
    };
    static selector = ".s_floating_blocks .s_floating_blocks_block";
}
