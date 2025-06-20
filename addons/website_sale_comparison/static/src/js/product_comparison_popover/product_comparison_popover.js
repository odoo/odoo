import { Component, onWillStart, useState, useSubEnv } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';
import { useBus } from '@web/core/utils/hooks';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductRow } from '../product_row/product_row';

export class ProductComparisonPopover extends Component {
    static template = 'website_sale_comparison.ProductComparisonPopover';
    static components = { ProductRow };
    static props = {
        bus: Object,
        currencyId: Number,
    };

    setup() {
        super.setup();
        useBus(
            this.props.bus,
            'comparison_add_product', // TODO(loti): not triggered because component doesn't exist yet.
            (ev) => this._addProduct(ev.detail.productId),
        );
        useBus(
            this.props.bus,
            'comparison_remove_product',
            (ev) => this._removeProduct(ev.detail.productId),
        );
        this.state = useState({ products: new Map() });
        useSubEnv({
            currency: { id: this.props.currencyId },
            removeProduct: this._removeProduct.bind(this),
        });
        onWillStart(this._loadProducts);
    }

    async _loadProducts() {
        const productIds = comparisonUtils.getComparisonProductIdsCookie();
        if (!productIds.length) return;
        const productData = await rpc('/shop/compare/get_product_data', {
            product_ids: productIds,
        });

        this.state.products.clear();
        productData.forEach((product) => this.state.products.set(product.id, product));
        if (productIds.length > productData.length) {
            comparisonUtils.setComparisonProductIdsCookie(this.state.products.keys());
        }
    }

    async _addProduct(productId) {
        const productIds = new Set(comparisonUtils.getComparisonProductIdsCookie());
        productIds.add(productId);
        comparisonUtils.setComparisonProductIdsCookie(productIds);
        await this._loadProducts();
    }

    _removeProduct(productId) {
        this.state.products.delete(productId);
        comparisonUtils.setComparisonProductIdsCookie(this.state.products.keys());
    }

    get comparisonUrl() {
        const productIds = Array.from(this.state.products.keys());
        return `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
    }
}
