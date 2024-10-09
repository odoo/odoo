import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductButton } from "./pricelist_option";

class ProductCatalogOptionPlugin extends Plugin {
    static id = "ProductCatalogOptionPlugin";
    resources = {
        builder_options: [
            withSequence(5, {
                selector: ".s_product_catalog",
                OptionComponent: AddProductButton,
                props: {
                    applyTo:
                        ":scope > :has(.s_product_catalog_dish):not(:has(.row > div .s_product_catalog_dish))",
                    productSelector: ".s_product_catalog_dish",
                },
            }),
            withSequence(5, {
                selector: ".s_product_catalog .row > div",
                OptionComponent: AddProductButton,
                props: {
                    applyTo: ":scope > :has(.s_product_catalog_dish)",
                    productSelector: ".s_product_catalog_dish",
                },
            }),
            withSequence(10, {
                template: "html_builder.ProductCatalogDescriptionOption",
                selector: ".s_product_catalog",
            }),
        ],
        dropzone_selector: {
            selector: ".s_product_catalog_dish",
            dropNear: ".s_product_catalog_dish",
        },
    };
}

registry.category("website-plugins").add(ProductCatalogOptionPlugin.id, ProductCatalogOptionPlugin);
