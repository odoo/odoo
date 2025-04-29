import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export class HeaderBorderOption extends BaseOptionComponent {
    static template = "website.HeaderBorderOption";
    static props = {};
    static components = { BorderConfigurator, ShadowOption };

    setup() {
        super.setup();
        this.domState = useDomState((editingElement) => ({
            withRoundCorner: !editingElement.classList.contains("o_header_force_no_radius"),
        }));
    }
}
