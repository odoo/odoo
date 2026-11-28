import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class WebsiteSaleHeaderIconsPlugin extends Plugin {
    static id = "websiteSaleHeaderIcons";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        header_icon_labels: [
            { name: "cart", label: _t("Cart Icon") },
            { name: "wishlist", label: _t("Wishlist Icon") },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WebsiteSaleHeaderIconsPlugin.id, WebsiteSaleHeaderIconsPlugin);
