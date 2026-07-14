import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class ImageAndFaOption extends BaseOptionComponent {
    static template = "html_builder.ImageAndFaOption";
    static components = { BorderConfigurator };
}
