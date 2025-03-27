import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class CartSuggestions extends Interaction {
    static selector = '.o_suggested_product';
    dynamicContent = {
        'button.js_add_suggested_products': { 't-on-click': this.addSuggestedProduct },
    };

    /**
     * @param {Event} ev
     */
    addSuggestedProduct(ev) {
        this.services['cart'].add({
            productTemplateId: parseInt(ev.currentTarget.dataset.productTemplateId),
            productId: parseInt(ev.currentTarget.dataset.productId),
            isCombo: ev.currentTarget.dataset.productType === 'combo',
        }, {
            isBuyNow: true,
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.cart_suggestions', CartSuggestions);
