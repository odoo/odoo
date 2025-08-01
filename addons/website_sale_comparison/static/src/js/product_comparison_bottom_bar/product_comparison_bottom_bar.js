import { Component, onWillStart, useState } from '@odoo/owl';
import { rpc } from '@web/core/network/rpc';
import { useBus, useService } from '@web/core/utils/hooks';
import { _t } from '@web/core/l10n/translation';
import { formatCurrency } from '@web/core/currency';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductRow } from '../product_row/product_row';

export class ProductComparisonBottomBar extends Component {
    static template = 'website_sale_comparison.ProductComparisonBottomBar';
    static components = { ProductRow };
    static props = {
        bus: Object,
    };

    setup() {
        super.setup();
        this.state = useState({
            products: new Map(),
            isVisible: false
        });
        this.dialogService = useService("dialog");
        useBus(this.props.bus, 'comparison_products_changed', (_) => this._loadProducts());
        onWillStart(this._loadProducts);
    }

    /**
     * Load the products to compare from the server.
     * This method also removes any products that are no longer available from the comparison.
     */
    async _loadProducts() {
        const productIds = comparisonUtils.getComparisonProductIds();
        this.state.isVisible = productIds.length > 0;

        if (!productIds.length) {
            this.state.products.clear();
            return;
        }

        const productData = await rpc('/shop/compare/get_product_data', {
            product_ids: productIds,
        });

        this.state.products.clear();
        // Preserve the order from the cookie by iterating productIds in order
        productIds.forEach((productId) => {
            const product = productData.find(p => p.id === productId);
            if (product) {
                this.state.products.set(product.id, product);
            }
        });

        if (productIds.length > productData.length) {
            comparisonUtils.setComparisonProductIds(Array.from(this.state.products.keys()));
        }
    }

    /**
     * Get the URL of the comparison page with the selected products.
     * @return {string} The URL of the comparison page.
     */
    get comparisonUrl() {
        const productIds = Array.from(this.state.products.keys());
        return `/shop/compare?products=${encodeURIComponent(productIds.join(','))}`;
    }

    /**
     * Get the count of products being compared.
     * @return {number} The number of products.
     */
    get productCount() {
        return this.state.products.size;
    }

    /**
     * Clear all products from the comparison.
     */
    clearAll() {
        const productCount = this.productCount;
        const title = productCount === 1
            ? _t("Remove Product")
            : _t("Clear Comparison");
        const body = productCount === 1
            ? _t("Are you sure you want to remove this product from comparison?")
            : _t("Are you sure you want to remove all %s products from comparison?", productCount);

        this.dialogService.add(ConfirmationDialog, {
            title: title,
            body: body,
            confirmLabel: _t("Clear all"),
            confirmClass: "btn-danger",
            confirm: () => {
                comparisonUtils.setComparisonProductIds([]);
                this.props.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));
            },
            cancel: () => {},
        });
    }

    /**
     * Navigate to the comparison page.
     */
    goToComparison() {
        if (this.productCount >= 2) {
            window.location.href = this.comparisonUrl;
        }
    }

    /**
     * Remove a specific product from the comparison.
     * @param {number} productId - The ID of the product to remove.
     */
    _removeProduct(productId) {
        comparisonUtils.removeComparisonProduct(productId);
        this.props.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));
    }

    /**
     * Format a price with currency symbol.
     * @param {number} price - The price to format.
     * @param {number} currencyId - The currency ID.
     * @return {string} The formatted price.
     */
    formatPrice(price, currencyId) {
        return formatCurrency(price, currencyId);
    }
}
