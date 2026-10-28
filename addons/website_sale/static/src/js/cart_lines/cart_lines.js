import { Component, onWillStart, t, useProps } from "@odoo/owl";
import { CartLine } from "./cart_line/cart_line";
import { CartAccessories } from "./cart_accessories/cart_accessories";
import wishlistUtils from "@website_sale/js/wishlist_utils";
import { formatCurrency } from "@web/core/currency";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { useSubEnv } from "@web/owl2/utils";

export class CartLines extends Component {
    static template = "website_sale.CartLines";
    static components = { CartLine, CartAccessories };
    props = useProps({ templateData: t.object() });

    setup() {
        this.cartService = useService("cart");
        onWillStart(async () => {
            await this.cartService.mutex.exec(
                async () => await this.cartService.loadCartData(false, false, true)
            );
        });

        useSubEnv({
            updateLine: this.updateLine.bind(this),
            addToWishlist: this.addToWishlist.bind(this),
            formatPrice: this.formatPrice.bind(this),
        });
    }

    async updateLine(lineId, productId, quantity) {
        await this.cartService.update(lineId, productId, quantity, true);
    }

    async addToWishlist(lineId, productId) {
        await rpc("/shop/wishlist/add", { product_id: productId });
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        await this.updateLine(lineId, productId, 0);
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }

    get data() {
        return this.cartService.state.lines;
    }

    get cartLinesProps() {
        return {
            isQuantityViewActive: this.data.is_quantity_view_active,
            isWishlistViewActive: this.data.is_wishlist_view_active,
            showProductReferencePrice: this.data.show_product_reference_price,
            templateData: this.props.templateData,
        };
    }

    get cartAccessoriesProps() {
        return {
            isQuantityViewActive: this.data.is_quantity_view_active,
            templateData: this.props.templateData,
            accessories: this.data.accessories,
        };
    }
}
