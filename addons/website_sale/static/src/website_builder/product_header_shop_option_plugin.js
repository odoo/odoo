import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class ProductHeaderShopOptionPlugin extends Plugin {
    static id = "ProductHeaderShopOptionPlugin";

    resources = {
        builder_options: {
            template: "website_sale.ProductHeaderShopOption",
            selector: "#products_grid:not(.o_wsale_is_category)",
            editableOnly: false,
            reloadTarget: true,
            title: _t("Shop Header"),
        },
    };
}

registry
    .category("website-plugins")
    .add(ProductHeaderShopOptionPlugin.id, ProductHeaderShopOptionPlugin);
