import { Component, t, useProps, usePlugin } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CartPlugin } from "@website_sale/js/cart_plugin";

export class CartAccessories extends Component {
    static template = "website_sale.CartAccessories";
    props = useProps({
        templateData: t.object(),
        accessories: t.array(),
    });
    cart = usePlugin(CartPlugin);

    setup() {
        this.cartService = useService("cart");
    }

    async addToCart(accessoryProduct) {
        const quantity = await this.cartService.add(
            {
                productTemplateId: accessoryProduct.product_tmpl_id,
                productId: accessoryProduct.id,
                isCombo: accessoryProduct.type == "combo",
            },
            {
                isBuyNow: true,
                redirectToCart: false,
                showNotification: false,
                showQuantity: this.cartService.state.is_quantity_view_active,
            }
        );
        if (quantity) {
            await this.cartService.loadCart({ force: true, withHistory: true });
        }
    }
}
