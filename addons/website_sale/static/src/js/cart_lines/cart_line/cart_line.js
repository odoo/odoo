import { Component, useState } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import { useDebounced } from '@web/core/utils/timing';

export const DELAY = 200;

export class CartLine extends Component {
	static template = 'website_sale.CartLine';
    static props = {
        id: Number,
        websiteUrl: String,
        isCombo: Boolean,
        isSellable: Boolean,
        productType: String,
        productId: Number,
        imageUri: String,
        nameShort: String,
        headerName: String,
        combinationName: String,
        hasMultipleUoms: Boolean,
        uomName: String,
        shouldShowStrikethroughPrice: Boolean,
        displayedQuantity: Number,
        displayedUnitPrice: Number,
        productUomQty: Number,
        productPrice: Number,
        baseUnitPrice: Number,
        productBaseUnitPrice: Number,
        descriptionLines: Array,
        shopWarning: String,
        comboItemLines: Array,
        isQuantityViewActive: Boolean,
        isWishlistViewActive: Boolean,
        currencyId: Number,
        isUomFeatureEnabled: Boolean,
        update: Function,
        addToWishlist: Function,
    }

    setup() {
        this.state = useState({
            quantity: this.props.displayedQuantity,
        })
        this.updateQuantityDebounced = useDebounced(() => {
            this.props.update(parseInt(this.props.id), this.props.productId, this.state.quantity);
        }, DELAY);
    }

	formatPrice(price) {
		return formatCurrency(price, this.props.currencyId);
	}

    updateQuantity(quantity) {
        const effectiveQuantity = parseInt(quantity);
        if (!Number.isNaN(effectiveQuantity) && effectiveQuantity !== this.state.quantity) {
            this.state.quantity = effectiveQuantity;
            this.updateQuantityDebounced();
        }
    }

    addToWishlist() {
        this.props.addToWishlist(parseInt(this.props.id), this.props.productId);
    }
}
