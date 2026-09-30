import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
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
    addProductFromWishlist(ev) {
        if (this._checkMaxComparisonProducts()) return;

        const el = ev.currentTarget;
        const productId = parseInt(el.dataset.productId);
        if (!productId || this._checkProductAlreadyInComparison(productId)) {
            comparisonUtils.updateDisabled(el, true);
            return;
        }

        comparisonUtils.addComparisonProduct(productId, this.bus);
        comparisonUtils.updateDisabled(el, true);
    },
});
