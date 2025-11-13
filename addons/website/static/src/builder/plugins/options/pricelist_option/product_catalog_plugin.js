import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { isElement } from "@html_editor/utils/dom_info";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { BaseAddProductOption } from "@html_builder/plugins/add_product_option";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

export class ProductCatalogDescriptionOption extends BaseOptionComponent {
    static template = "website.ProductCatalogDescriptionOption";
    static selector = ".s_product_catalog";
    static components = { BorderConfigurator };
}

export class AddProductCatalogOption extends BaseAddProductOption {
    static selector = ".s_product_catalog";
    buttonApplyTo =
        ":scope > :has(.s_product_catalog_dish):not(:has(.row > div .s_product_catalog_dish))";
    productSelector = ".s_product_catalog_dish";
}

export class AddProductCatalogSectionOption extends BaseAddProductOption {
    static selector = ".s_product_catalog .row > div";
    buttonApplyTo = ":scope > :has(.s_product_catalog_dish)";
    productSelector = ".s_product_catalog_dish";
}

class ProductCatalogOptionPlugin extends Plugin {
    static id = "productCatalogOptionPlugin";
    resources = {
        builder_options: [
            withSequence(BEGIN, AddProductCatalogOption),
            withSequence(BEGIN, AddProductCatalogSectionOption),
            withSequence(SNIPPET_SPECIFIC_END, ProductCatalogDescriptionOption),
        ],
        dropzone_selector: {
            selector: ".s_product_catalog_dish",
            dropNear: ".s_product_catalog_dish",
        },
        is_movable_selector: { selector: ".s_product_catalog_dish", direction: "vertical" },
        // Protect pricelist item, price, and description blocks from being
        // split/merged by the delete plugin.
        unsplittable_node_predicates: (node) =>
            isElement(node) &&
            node.matches(
                ".s_product_catalog_dish, .s_product_catalog_dish_price, .s_product_catalog_dish_description"
            ),
    };
}

registry.category("website-plugins").add(ProductCatalogOptionPlugin.id, ProductCatalogOptionPlugin);
