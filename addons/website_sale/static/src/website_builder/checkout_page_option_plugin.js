import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { WebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";

export class CheckoutPageOption extends BaseOptionComponent {
    static template = "website_sale.checkoutPageOption";
    static selector = "main:has(.oe_website_sale .o_wizard)";
    static title = _t("Checkout Pages");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class CheckoutPageOptionPlugin extends Plugin {
    static id = "checkoutPageOption";
    resources = {
        builder_options: [CheckoutPageOption],
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
