
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class WishlistPageOptionPlugin extends Plugin {
    static id = "wishlistPageOption";
    resources = {
        builder_options: [
            {
                template: "website_sale_wishlist.WishlistPageOption",
                selector: "#o_comparelist_table",
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
