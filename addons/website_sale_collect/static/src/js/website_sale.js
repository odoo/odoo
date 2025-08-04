import { Component } from '@odoo/owl';
import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #product_stock_notification_message': '_onClickProductStockNotificationMessage',
        'click #product_stock_notification_form_submit_button': '_onClickSubmitProductStockNotificationForm',
    }),

    _onClickProductStockNotificationMessage(ev) {
        this._handleClickStockNotificationMessage(ev);
    },

    _onClickSubmitProductStockNotificationForm(ev) {
        const formEl = ev.currentTarget.closest('#stock_notification_form');
        const productId = parseInt(formEl.querySelector('input[name="product_id"]').value);
        this._handleClickSubmitStockNotificationForm(ev, productId);
    },

    /**
     * Trigger a state update of the ClickAndCollectAvailability component when the combination info
     * is updated.
     *
     * @override
     */
    _onChangeCombination(ev, $parent, combination) {
        const res = this._super.apply(this, arguments);
        Component.env.bus.trigger('updateCombinationInfo', combination);
        return res;
    },
})
