import { patch } from '@web/core/utils/patch';
import { renderToElement } from '@web/core/utils/render';
import { patchDynamicContent } from '@web/public/utils';
import { ProductPage } from '@website_sale/interactions/product_page';

patch(ProductPage.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '#wishlist_stock_notification_message': {
                't-on-click': this.onClickWishlistStockNotificationMessage.bind(this),
            },
            '#wishlist_stock_notification_form_submit_button': {
                't-on-click': this.onClickSubmitWishlistStockNotificationForm.bind(this),
            },
        });
    },

    onClickWishlistStockNotificationMessage(ev) {
        this._handleClickStockNotificationMessage(ev);
    },

    onClickSubmitWishlistStockNotificationForm(ev) {
        const productId = ev.currentTarget.closest('article').dataset.productId;
        this._handleClickSubmitStockNotificationForm(ev, productId);
    },

    /**
     * Override of `website_sale` to display additional info messages regarding the product's stock
     * and the wishlist.
     *
     * @param {Event} ev
     * @param {Element} parent
     * @param {Object} combination
     */
    _onChangeCombination(ev, parent, combination) {
        super._onChangeCombination(...arguments);
        if (this.el.querySelector('.o_add_wishlist_dyn')) {
            const messageEl = this.el.querySelector('div.availability_messages');
            if (messageEl && !this.el.querySelector('#stock_wishlist_message')) {
                this.services['public.interactions'].stopInteractions(messageEl);
                messageEl.append(
                    renderToElement('website_sale_stock_wishlist.product_availability', combination)
                    || ''
                );
                this.services['public.interactions'].startInteractions(messageEl);
            }
        }
    },
});
