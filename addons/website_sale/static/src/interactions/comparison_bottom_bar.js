import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import {
    ProductComparisonBottomBar
} from '@website_sale/js/product_comparison_bottom_bar/product_comparison_bottom_bar';

export class ComparisonBottomBar extends Interaction {
    static selector = 'main:has(.o_wsale_product_page, .o_wsale_products_page, .o_wsale_wishlist_page, .s_dynamic_snippet_products)';

    setup() {
        const customBorderEl = this.el.querySelector('.o_wsale_custom_border_color, .o_wsale_custom_border_width');
        const borderStyle = customBorderEl && getComputedStyle(customBorderEl);
        this.mountComponent(this.el, ProductComparisonBottomBar, {
            borderColor: borderStyle?.getPropertyValue('--o-wsale-border-color').trim() || undefined,
            borderWidth: borderStyle?.getPropertyValue('--o-wsale-border-width').trim() || undefined,
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.comparison_bottom_bar', ComparisonBottomBar);
