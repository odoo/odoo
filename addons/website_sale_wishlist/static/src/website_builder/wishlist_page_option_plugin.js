import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WishlistPageOptionPlugin extends Plugin {
    static id = "wishlistPageOption";
    resources = {
        builder_options: [
            {
                template: "website_sale_wishlist.WishlistPageOption",
                selector: "main:has(.o_wsale_wishlist)",
                editableOnly: false,
                title: _t("Wishlist Page"),
                groups: ["website.group_website_designer"],
            },
        ],
    };
}

registry
    .category("website-plugins")
    .add(WishlistPageOptionPlugin.id, WishlistPageOptionPlugin);
