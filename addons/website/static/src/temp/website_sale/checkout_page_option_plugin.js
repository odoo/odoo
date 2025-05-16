import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class CheckoutPageOptionPlugin extends Plugin {
    static id = "checkoutPageOption";
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
    };
}

registry.category("website-plugins").add(CheckoutPageOptionPlugin.id, CheckoutPageOptionPlugin);
