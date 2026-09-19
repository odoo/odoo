import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";
export class HeaderBoxOption extends BaseOptionComponent {
    static id = "header_box_option";
    static template = "website.HeaderBoxOption";
    static components = { WebsiteBorderConfigurator };

    setup() {
        super.setup();
        this.domState = useDomState((editingElement) => ({
            withRoundCorner: !editingElement.classList.contains("o_header_force_no_radius"),
        }));
    }
}

registry.category("website-options").add(HeaderBoxOption.id, HeaderBoxOption);
