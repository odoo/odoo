import { AddToCartOptionPlugin } from "../website_builder/add_to_cart_option_plugin";
import { CheckoutPageOptionPlugin } from "../website_builder/checkout_page_option_plugin";
import { DynamicSnippetProductsOptionPlugin } from "../website_builder/dynamic_snippet_products_option_plugin";
import { ProductPageOptionPlugin } from "../website_builder/product_page_option_plugin";
import { ProductsRibbonOptionPlugin } from "../website_builder/product_ribbon_options_plugin";
import { ProductsItemOptionPlugin } from "../website_builder/products_item_option_plugin";

declare module "plugins" {
    interface SharedMethods {
        addToCartOption: SharedOf<typeof AddToCartOptionPlugin>;
        checkoutPageOption: SharedOf<typeof CheckoutPageOptionPlugin>;
        dynamicSnippetProductsOption: SharedOf<typeof DynamicSnippetProductsOptionPlugin>;
        productPageOption: SharedOf<typeof ProductPageOptionPlugin>;
        productsItemOptionPlugin: SharedOf<typeof ProductsItemOptionPlugin>;
        productsRibbonOptionPlugin: SharedOf<typeof ProductsRibbonOptionPlugin>;
    }
}
