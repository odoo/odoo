
import { patch } from '@web/core/utils/patch';
import { ExpressCheckout } from '@payment/interactions/express_checkout';

patch(ExpressCheckout.prototype, {
    start() {
        super.start();
        // Monitor updates of the amount on eCommerce's cart pages.
        this.services.cart.bus.addEventListener('cart_amount_changed', (ev) =>
            this._updateAmount(...ev.detail)
        );
    }
});
