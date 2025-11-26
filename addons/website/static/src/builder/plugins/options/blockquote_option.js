import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { BaseWebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";

export class BaseBlockquoteOption extends BaseOptionComponent {
    static id = "base_blockquote_option";
    static template = "website.BlockquoteOption";
    static components = {
        BaseWebsiteBackgroundOption,
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

registry.category("builder-options").add(BaseBlockquoteOption.id, BaseBlockquoteOption);
