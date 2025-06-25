import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { WebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";

class CheckoutPageOptionPlugin extends Plugin {
    static id = "checkoutPageOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            {
                template: "website_sale.checkoutPageOption",
                selector: "main:has(.oe_website_sale .o_wizard)",
                editableOnly: false,
                title: _t("Checkout Pages"),
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: {
            SetExtraStepAction,
        },
    };
}

export class SetExtraStepAction extends WebsiteConfigAction {
    static id = "setExtraStep";
    async apply(context) {
        await Promise.all([
            super.apply(context),
            rpc("/shop/config/website", { extra_step: "true" }),
        ]);
    }
    async clean(context) {
        await Promise.all([
            super.clean(context),
            rpc("/shop/config/website", { extra_step: "false" }),
        ]);
    }
}

registry.category("website-plugins").add(CheckoutPageOptionPlugin.id, CheckoutPageOptionPlugin);
