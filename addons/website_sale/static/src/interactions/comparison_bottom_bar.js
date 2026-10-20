import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import {
    ProductComparisonBottomBar
} from '@website_sale/js/product_comparison_bottom_bar/product_comparison_bottom_bar';
import comparisonUtils from '@website_sale/js/comparison_utils';

export class ComparisonBottomBar extends Interaction {
    static selector = '.o_wsale_product_page, .o_wsale_products_page, .o_wsale_wishlist_page';
    dynamicContent = {
        _window: { 't-on-pageshow': this.onPageShow },
    };

    setup() {
        // Mount the ProductComparisonBottomBar on pages with comparison functionality.
        this.mountComponent(this.el, ProductComparisonBottomBar);
    }

    /**
     * Refresh comparison state changed on another page while this page was cached.
     *
     * @param {PageTransitionEvent} ev
     */
    onPageShow(ev) {
        if (!ev.persisted) return;
        const productIds = comparisonUtils.getComparisonProductIds();
        const buttons = this.el.querySelectorAll(
            '.o_add_compare, .o_add_compare_dyn, .o_add_to_compare'
        );
        for (const button of buttons) {
            const productId = parseInt(button.dataset.productId);
            button.disabled = productIds.includes(productId);
        }
        comparisonUtils.notifyComparisonListeners(this.env.bus);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.comparison_bottom_bar', ComparisonBottomBar);
