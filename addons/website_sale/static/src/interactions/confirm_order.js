import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class ConfirmOrder extends Interaction {
    static selector = 'form[name="o_wsale_confirm_order"]';
    dynamicContent = {
        _root: { 't-on-submit': this.locked(this.onConfirmOrder) },
    };

    /**
     * Prevent multiple clicks on the confirm button when the form is being submitted.
     *
     * @param {Event} ev
     */
    onConfirmOrder(ev) {
        const button = ev.currentTarget.querySelector('button[type="submit"]');
        button.disabled = true;
        // TODO(loti): "random" timeout seems brittle.
        this.waitForTimeout(() => button.disabled = false, 5000);
    }
}

registry.category('public.interactions').add('website_sale.confirm_order', ConfirmOrder);
