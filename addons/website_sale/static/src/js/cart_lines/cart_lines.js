import { Component, onWillStart, proxy, props, t } from "@odoo/owl";
import { CartLine } from "./cart_line/cart_line";
import { CartAccessories } from "./cart_accessories/cart_accessories";
import wishlistUtils from "@website_sale/js/wishlist_utils";
import { formatCurrency } from "@web/core/currency";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { useSubEnv } from "@web/owl2/utils";

export class CartLines extends Component {
    static template = "website_sale.CartLines";
    static components = { CartLine, CartAccessories };
    props = props({ templateData: t.object() });

    setup() {
        this.cartService = useService("cart");
        this.state = proxy({
            currency_id: null,
            cart_lines: [],
            accessories: [],
            is_quantity_view_active: false,
            is_wishlist_view_active: false,
            is_uom_feature_enabled: false,
            is_accessories_view_active: false,
        });

        onWillStart(async () => {
            await this.updateLines();
        });

        useBus(this.cartService.bus, "cart_update", async () => {
            await this.updateLines();
        });

        useSubEnv({
            updateLine: this.updateLine.bind(this),
            addToWishlist: this.addToWishlist.bind(this),
            formatPrice: this.formatPrice.bind(this),
        });
    }

    async updateLines() {
        const data = await rpc("/shop/cart/lines");
        Object.assign(this.state, data);
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
        return formatCurrency(price, this.state.currency_id);
    }

    get cartLinesProps() {
        return {
            isQuantityViewActive: this.state.is_quantity_view_active,
            isWishlistViewActive: this.state.is_wishlist_view_active,
            isUomFeatureEnabled: this.state.is_uom_feature_enabled,
            templateData: this.props.templateData,
        };
    }

    get cartAccessoriesProps() {
        return {
            isQuantityViewActive: this.state.is_quantity_view_active,
            templateData: this.props.templateData,
            accessories: this.state.accessories,
        };
    }
}
