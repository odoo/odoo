import { Component, onWillStart, useState } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';
import { useBus } from '@web/core/utils/hooks';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductRow } from '../product_row/product_row';

export class ProductComparisonPopover extends Component {
    static template = 'website_sale_comparison.ProductComparisonPopover';
    static components = { ProductRow };
    static props = {
        close: Function,
    };

    setup() {
        super.setup();
        this.state = useState({ products: new Map() });
        useBus(this.env.bus, 'comparison_products_changed', (_) => this._loadProducts());
        onWillStart(this._loadProducts);
    }

    /**
     * Load the products to compare from the server.
     *
     * This method also removes any products that are no longer available from the comparison.
     */
    async _loadProducts() {
        const productIds = comparisonUtils.getComparisonProductIds();
        if (!productIds.length) return;
        const productData = await rpc('/shop/compare/get_product_data', {
            product_ids: productIds,
        });

        this.state.products.clear();
        productData.forEach((product) => this.state.products.set(product.id, product));
        if (productIds.length > productData.length) {
            comparisonUtils.setComparisonProductIds(this.state.products.keys());
        }
    }

    /**
     * Get the URL of the comparison page with the selected products.
     *
     * @return {string} The URL of the comparison page.
     */
    get comparisonUrl() {
        const productIds = Array.from(this.state.products.keys());
        return `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
    }
}
