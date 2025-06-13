import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { utils as uiUtils } from '@web/core/ui/ui_service';

export class CartNavigation extends Interaction {
    static selector = '.o_website_sale_checkout';

    /**
     * For mobile screens, `.o_cta_navigation_container` has an absolute position causing
     * overlapping issues with nearby divs, therefore the height of `.o_website_sale_checkout` needs
     * to include the height of the absolute div and needs to be updated every time an element on
     * the checkout is expanded (i.e. payment methods, cart summary)
     */
    setup() {
        const ctaNavigation = this.el.querySelector('.o_cta_navigation_container');
        if (uiUtils.isSmall() && ctaNavigation) {
            const updateCheckoutHeight = () => {
                const updatedHeight = ctaNavigation.offsetTop + ctaNavigation.offsetHeight;
                this.el.style.height = `${updatedHeight}px`;
            }
            this.resizeObserver = new ResizeObserver(updateCheckoutHeight);
            const paymentForm = document.getElementById('o_payment_form');
            const cartSummary = document.getElementById('o_wsale_accordion_item');
            if (paymentForm) this.resizeObserver.observe(paymentForm);
            if (cartSummary) this.resizeObserver.observe(cartSummary);
        }
    }

    destroy() {
        this.resizeObserver?.disconnect();
    }
}

registry
    .category('public.interactions')
    .add('website_sale.cart_navigation', CartNavigation);
