import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class FontAwesomeOption extends BaseOptionComponent {
    static template = "html_builder.FontAwesomeOption";
    static selector = "span.fa, i.fa";
    static components = { BorderConfigurator };
}
