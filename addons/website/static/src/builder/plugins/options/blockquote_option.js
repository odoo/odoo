import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export class BlockquoteOption extends BaseOptionComponent {
    static template = "website.BlockquoteOption";
    static components = {
        WebsiteBackgroundOption,
        BorderConfigurator,
        ShadowOption,
    };
    static props = {
        disableWidth: { type: Boolean, optional: true },
    };
    static defaultProps = {
        disableWidth: false,
    };
    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
    }
}
