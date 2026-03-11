import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useGetItemValue } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";

export class BlockquoteOption extends BaseOptionComponent {
    static id = "blockquote_option";
    static template = "website.BlockquoteOption";
    static components = {
        WebsiteBackgroundOption,
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

registry.category("website-options").add(BlockquoteOption.id, BlockquoteOption);
