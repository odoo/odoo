import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class CartSuggestion extends Interaction {
    static selector = '[name="suggested_product"]';
    dynamicContent = {
        'button.js_add_suggested_products': { 't-on-click': this.addSuggestedProduct },
    };

    /**
     * @param {Event} ev
     */
    addSuggestedProduct(ev) {
        const dataset = ev.currentTarget.dataset;
        this.services['cart'].add({
            productTemplateId: parseInt(dataset.productTemplateId),
            productId: parseInt(dataset.productId),
            isCombo: dataset.productType === 'combo',
        }, {
            isBuyNow: true,
            showQuantity: Boolean(dataset.showQuantity),
        });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.cart_suggestion', CartSuggestion);
