import { BEGIN, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { AddProductOption } from "./add_product_option";

class ProductCatalogOptionPlugin extends Plugin {
    static id = "productCatalogOptionPlugin";
    resources = {
        builder_options: [
            withSequence(BEGIN, {
                selector: ".s_product_catalog",
                OptionComponent: AddProductOption,
                props: {
                    applyTo:
                        ":scope > :has(.s_product_catalog_dish):not(:has(.row > div .s_product_catalog_dish))",
                    productSelector: ".s_product_catalog_dish",
                },
            }),
            withSequence(BEGIN, {
                selector: ".s_product_catalog .row > div",
                OptionComponent: AddProductOption,
                props: {
                    applyTo: ":scope > :has(.s_product_catalog_dish)",
                    productSelector: ".s_product_catalog_dish",
                },
            }),
            withSequence(SNIPPET_SPECIFIC_END, {
                template: "website.ProductCatalogDescriptionOption",
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
