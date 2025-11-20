import { Component, onWillStart, useState } from '@odoo/owl';
import { useService, useBus } from '@web/core/utils/hooks';
import { redirect } from '@web/core/utils/urls';
import { rpc } from '@web/core/network/rpc';
import { CartLine } from './cart_line/cart_line';
import wishlistUtils from '@website_sale/js/wishlist_utils';

export class CartLines extends Component {
    static template = 'website_sale.CartLines';
    static props = {};
    static components = { CartLine };

    setup() {
        this.cartService = useService('cart');
        this.state = useState({
            shopWarning: '',
            currencyId: null,
            cartLines: [],
            isQuantityViewActive: false,
            isWishlistViewActive: false,
        });

        onWillStart(async () => {
            await this.updateLines();
        });

        useBus(this.cartService.bus, 'cart_update', async () => {
            await this.updateLines();
        });
    }

    async updateLines() {
        const data = await rpc('/shop/cart/lines');
        if (!data.cart_lines.length) {
            return redirect('/shop/cart');
        }
        this.state.cartLines = data['cart_lines'];
        this.state.shopWarning = data['shop_warning'];
        this.state.isQuantityViewActive = data['is_quantity_view_active'];
        this.state.isWishlistViewActive = data['is_wishlist_view_active'];
        this.state.isUomFeatureEnabled = data['is_uom_feature_enabled'];
        this.state.currencyId = data['currency_id'];
    }

    updateLine(lineId, productId, quantity) {
        this.cartService.update(lineId, productId, quantity);
    }

    async addToWishlist(lineId, productId) {
        await rpc('/shop/wishlist/add', { product_id: productId });
        wishlistUtils.addWishlistProduct(productId);
        wishlistUtils.updateWishlistNavBar();
        this.updateLine(lineId, productId, 0);
    }

    getLineProps(line) {
        return {
            id: line.id,
            websiteUrl: line.website_url,
            isCombo: line.is_combo,
            isSellable: line.is_sellable,
            productType: line.product_type,
            productId: line.product_id,
            imageUri: line.image_uri,
            nameShort: line.name_short,
            headerName: line.header_name,
            combinationName: line.combination_name,
            hasMultipleUoms: line.has_multiple_uoms,
            uomName: line.uom_name,
            shouldShowStrikethroughPrice: line.should_show_strikethrough_price,
            displayedQuantity: line.displayed_quantity,
            displayedUnitPrice: line.displayed_unit_price,
            productPrice: line.product_price,
            baseUnitPrice: line.base_unit_price,
            productUomQty: line.product_uom_qty,
            productBaseUnitPrice: line.product_base_unit_price,
            descriptionLines: line.description_lines,
            shopWarning: line.shop_warning,
            comboItemLines: line.combo_item_lines,
            isQuantityViewActive: this.state.isQuantityViewActive,
            isWishlistViewActive: this.state.isWishlistViewActive,
            currencyId: this.state.currencyId,
            isUomFeatureEnabled: this.state.isUomFeatureEnabled,
            update: this.updateLine.bind(this),
            addToWishlist: this.addToWishlist.bind(this),
        };
    }
}
