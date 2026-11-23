import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CartAccessories extends Component {
    static template = "website_sale.CartAccessories";
    props = useProps({
        templateData: t.object(),
        accessories: t.array(),
    });

    setup() {
        this.cartService = useService("cart");
    }

    async addToCart(accessoryProduct) {
        await this.cartService.add(
            {
                productTemplateId: accessoryProduct.product_tmpl_id,
                productId: accessoryProduct.id,
                isCombo: accessoryProduct.type == "combo",
                ...this._getOptionalAddToCartParams(),
            },
            {
                isBuyNow: true,
                redirectToCart: false,
                showNotification: false,
                showQuantity: this.cartService.state.is_quantity_view_active,
            }
        );
    }

    _getOptionalAddToCartParams() {
        return {};
    }
}
