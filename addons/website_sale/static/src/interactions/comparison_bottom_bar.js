import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import {
    ProductComparisonBottomBar
} from '@website_sale/js/product_comparison_bottom_bar/product_comparison_bottom_bar';

export class ComparisonBottomBar extends Interaction {
    static selector = '.o_wsale_product_page, .o_wsale_products_page, .o_wsale_wishlist_page';

    setup() {
        // Mount the ProductComparisonBottomBar on pages with comparison functionality.
        this.mountComponent(this.el, ProductComparisonBottomBar);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.comparison_bottom_bar', ComparisonBottomBar);
