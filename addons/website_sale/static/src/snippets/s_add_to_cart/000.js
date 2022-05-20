/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { cartHandlerMixin } from 'website_sale.utils'
import { WebsiteSale } from 'website_sale.website_sale';

publicWidget.registry.AddToCartSnippet = WebsiteSale.extend(cartHandlerMixin, {
    selector: '.s_add_to_cart',
    events: {
        'click #s_add_to_cart_button': '_onClickAddToCartButton',
    },

    _onClickAddToCartButton(ev) {
        const dataset = ev.currentTarget.dataset;

        const visitorChoice = dataset.visitorChoice;
        const action = dataset.action;
        const productId = dataset.productVariant;

        if (!productId) return;

        if (visitorChoice) {
            this._handleVisitorChoice(ev)
        } else {
            this._handleAddToCart(productId, action);
        }
    },

    _handleVisitorChoice(ev) {
        const $form = $(ev.currentTarget).closest('form');
        this._handleAdd($form);
    },

    _handleAddToCart(productId, action) {
        const params = {
            product_id: parseInt(productId),
            add_qty: 1
        };
        this.getRedirectOption();
        this.isBuyNow = action === 'buy_now';
        this.addToCart(params);
    },
});

export default publicWidget.registry.AddToCartSnippet
