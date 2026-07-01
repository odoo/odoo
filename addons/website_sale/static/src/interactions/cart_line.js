import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { CartLines as CartLinesComponent } from "@website_sale/js/cart_lines/cart_lines";
import wSaleUtils from "@website_sale/js/website_sale_utils";

export class CartLine extends Interaction {
    static selector = "#cart_products";
    dynamicContent = {
        _root: {
            "t-component": (el) => {
                const root = el.parentElement;

                const selectors = {
                    removeButtonText: "#cart_products_edit_mode .cart_remove",
                    wishlistButtonText: "#cart_products_edit_mode .cart_wishlist",
                    qtyMinusButtonText: "#cart_products_edit_mode .cart_quantity_minus",
                    qtyPlusButtonText: "#cart_products_edit_mode .cart_quantity_plus",
                    qtyMinusButtonTextMobile:
                        "#cart_products_edit_mode .cart_quantity_minus_mobile",
                    qtyPlusButtonTextMobile: "#cart_products_edit_mode .cart_quantity_plus_mobile",
                    emptyCartTitle: "#empty_cart_edit_mode .empty_cart_title",
                    shopButtonTitle: "#empty_cart_edit_mode .shop_button_title",
                    accessoriesTitle: "#cart_products_edit_mode h5.accessory_products_title",
                    addToCartButtonText: "#cart_products_edit_mode .add_to_cart_button",
                };

                const templateData = wSaleUtils.extractEditModeText(root, selectors);

                return [CartLinesComponent, { templateData }];
            },
        },
    };
}

registry.category("public.interactions").add("website_sale.cart_line", CartLine);
