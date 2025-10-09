import { EventBus } from '@odoo/owl';
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import {
    ProductComparisonBottomBar
} from '@website_sale_comparison/js/product_comparison_bottom_bar/product_comparison_bottom_bar';

export class AddToComparison extends Interaction {
    static selector = '.o_add_compare, .o_add_compare_dyn';
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _productEl: () => document.querySelector('.js_product'),
    };
    dynamicContent = {
        _root: { 't-on-click': this.addProduct },
        _productEl: { 't-on-product_changed': this.onProductChanged },
    };

    setup() {
        this.bus = new EventBus();
        // Mount the ProductComparisonBottomBar on pages with comparison functionality
        this.mountComponent(
            document.querySelector('.js_sale:not(.o_wsale_comparison_page)'),
            ProductComparisonBottomBar,
            {
                bus: this.bus,
            },
        );
    }

    /**
     * Add a product to the comparison.
     *
     * @param {Event} ev
     */
    async addProduct(ev) {
        if (this._checkMaxComparisonProducts()) return;

        const el = ev.currentTarget;
        let productId = parseInt(el.dataset.productProductId);
        if (!productId) {
            const productEl = el.closest('.js_product');
            productId = await this.waitFor(rpc('/sale/create_product_variant', {
                product_template_id: parseInt(el.dataset.productTemplateId),
                product_template_attribute_value_ids: wSaleUtils.getSelectedAttributeValues(productEl),
            }));
        }
        if (!productId || this._checkProductAlreadyInComparison(productId)) {
            comparisonUtils.updateDisabled(el, true);
            return;
        }

        comparisonUtils.addComparisonProduct(productId, this.bus);
        comparisonUtils.updateDisabled(el, true);
    }

    /**
     * Enable/disable the "add to comparison" button based on the selected variant.
     *
     * @param {CustomEvent} event
     */
    onProductChanged(event) {
        const input = event.target;
        const button = input.closest('.js_product')?.querySelector('[data-action="o_comparelist"]');
        if (button) {
        const { productId } = event.detail;
            const isDisabled = comparisonUtils.getComparisonProductIds().includes(
                parseInt(productId)
            );
            comparisonUtils.updateDisabled(button, isDisabled);
            button.dataset.productProductId = productId;
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Check whether the maximum number of products in the comparison has been reached, and if so,
     * show a warning.
     *
     * @return {boolean} Whether the maximum number of products in the comparison has been reached.
     */
    _checkMaxComparisonProducts() {
        if (
            comparisonUtils.getComparisonProductIds().length
            >= comparisonUtils.MAX_COMPARISON_PRODUCTS
        ) {
            this.services.notification.add(
                _t("You can compare up to 4 products at a time."),
                {
                    type: 'warning',
                    sticky: false,
                    title: _t("Too many products to compare"),
                },
            );
            return true;
        }
        return false;
    }

    /**
     * Check whether the product is already in the comparison, and if so, show a warning.
     *
     * @param productId The ID of the product to check.
     * @return {boolean} Whether the product is already in the comparison.
     */
    _checkProductAlreadyInComparison(productId) {
        if (comparisonUtils.getComparisonProductIds().includes(productId)) {
            this.services.notification.add(
                _t("This product has already been added to the comparison."),
                { type: 'warning', sticky: false },
            );
            return true;
        }
        return false;
    }
}

registry
    .category('public.interactions')
    .add('website_sale_comparison.add_to_comparison', AddToComparison);
