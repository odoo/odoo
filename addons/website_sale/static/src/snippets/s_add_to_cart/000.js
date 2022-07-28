/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { cartHandlerMixin } from 'website_sale.utils';
import { WebsiteSale } from 'website_sale.website_sale';
import { _t } from 'web.core';

publicWidget.registry.AddToCartSnippet = WebsiteSale.extend(cartHandlerMixin, {
    selector: '.s_add_to_cart_btn',
    events: {
        'click': '_onClickAddToCartButton',
    },

    _onClickAddToCartButton: async function (ev) {
        const dataset = ev.currentTarget.dataset;

        const visitorChoice = dataset.visitorChoice === 'true';
        const action = dataset.action;
        const productId = parseInt(dataset.productVariantId);

        if (!productId) {
            return;
        }

        if (visitorChoice) {
            this._handleAdd($(ev.currentTarget.closest('div')));
        } else {
            const isAddToCartAllowed = await this._rpc({
                route: `/shop/product/is_add_to_cart_allowed`,
                params: {
                    product_id: productId,
                },
            });
            if (!isAddToCartAllowed) {
                this.displayNotification({
                    title: 'User Error',
                    message: _t('This product does not exist therefore it cannot be added to cart.'),
                    type: 'warning'
                });
                return;
            }
            this.isBuyNow = action === 'buy_now';
            this.stayOnPageOption = !this.isBuyNow;
            this.addToCart({product_id: productId, add_qty: 1});
        }
    },
});

export default publicWidget.registry.AddToCartSnippet;
