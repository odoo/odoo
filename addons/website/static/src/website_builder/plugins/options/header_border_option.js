import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BorderConfigurator } from "@website/temp/plugins/border_configurator_option";
import { ShadowOption } from "@website/temp/plugins/shadow_option";

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
