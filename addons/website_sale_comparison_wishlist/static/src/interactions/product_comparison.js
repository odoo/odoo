import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import { ProductComparison } from '@website_sale_comparison/interactions/product_comparison';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';

patch(ProductComparison.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '.wishlist-section .o_add_to_compare': {
                't-on-click': this.addProductFromWishlist.bind(this),
            },
        });
    },

    /**
     * Add a product to the comparison from the wishlist page.
     *
     * @param {Event} ev
     */
    async addProductFromWishlist(ev) {
        if (this._checkMaxComparisonProducts()) return;

        const el = ev.currentTarget;
        const productId = parseInt(el.dataset.productId);
        if (!productId || this._checkProductAlreadyInComparison(productId)) {
            this._updateDisabled(el, true);
            return;
        }

        comparisonUtils.addComparisonProduct(productId);
        this.bus.dispatchEvent(new CustomEvent('comparison_products_changed', { bubbles: true }));
        this._updateDisabled(el, true);
        await wSaleUtils.animateClone(
            $('button[name="product_comparison_button"]'), $(el.closest('tr')), -50, 10
        );
    },
});
