import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useGetItemValue } from "@html_builder/core/utils";
import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { WebsiteBorderConfigurator } from "@website/builder/plugins/options/website_border_configurator_option";

export class BlockquoteOption extends BaseOptionComponent {
    static id = "blockquote_option";
    static template = "website.BlockquoteOption";
    static components = {
        WebsiteBackgroundOption,
        WebsiteBorderConfigurator,
    };
    props = props({
        disableWidth: t.boolean().optional(false),
    });
    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
    }
}

registry.category("website-options").add(BlockquoteOption.id, BlockquoteOption);
