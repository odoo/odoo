import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

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
        builder_actions: this.getActions(),
    };
    getActions() {
        const plugin = this;
        return {
            get setExtraStep() {
                const websiteConfigAction =
                    plugin.dependencies.builderActions.getAction("websiteConfig");
                return {
                    ...websiteConfigAction,
                    apply: async (...args) => {
                        await Promise.all([
                            websiteConfigAction.apply(...args),
                            rpc("/shop/config/website", { extra_step: "true" }),
                        ]);
                    },
                    clean: async (...args) => {
                        await Promise.all([
                            websiteConfigAction.clean(...args),
                            rpc("/shop/config/website", { extra_step: "false" }),
                        ]);
                    },
                };
            },
        };
    }
}

registry.category("website-plugins").add(CheckoutPageOptionPlugin.id, CheckoutPageOptionPlugin);
