import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class ProductHeaderCategoryOptionPlugin extends Plugin {
    static id = "ProductHeaderCategoryOptionPlugin";

    resources = {
        builder_options: {
            template: "website_sale.ProductHeaderCategoryOption",
            selector: "#products_grid.o_wsale_is_category",
            editableOnly: false,
            reloadTarget: true,
            title: _t("Categories Header"),
        },
    };
}

registry
    .category("website-plugins")
    .add(ProductHeaderCategoryOptionPlugin.id, ProductHeaderCategoryOptionPlugin);
