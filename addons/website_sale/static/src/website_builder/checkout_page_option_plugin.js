import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { WebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";

export class CheckoutPageOptionPlugin extends Plugin {
    static id = "checkoutPageOption";
    resources = {
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
