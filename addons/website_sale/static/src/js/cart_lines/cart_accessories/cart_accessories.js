import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CartAccessories extends Component {
    static template = "website_sale.CartAccessories";
    static props = {
        isQuantityViewActive: Boolean,
        templateData: Object,
        accessories: Object,
    };

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
                source: "cart_accessory",
                showQuantity: this.props.isQuantityViewActive,
            },
        );
    }

    _getOptionalAddToCartParams() {
        return {};
    }
}
