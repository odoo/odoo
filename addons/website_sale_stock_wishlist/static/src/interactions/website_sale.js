import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { WebsiteSale } from '@website_sale/interactions/website_sale';

patch(WebsiteSale.prototype, {
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
});
