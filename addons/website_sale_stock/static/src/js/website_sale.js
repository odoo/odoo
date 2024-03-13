/** @odoo-module alias=website_sale_stock.website_sale**/

import { WebsiteSale } from 'website_sale.website_sale';
import { is_email } from 'web.utils';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #product_stock_notification_message': '_onClickProductStockNotificationMessage',
        'click #product_stock_notification_form_submit_button': '_onClickSubmitProductStockNotificationForm',
    }),

    _onClickProductStockNotificationMessage: function (ev) {
        const partnerEmail = document.querySelector('#wsale_user_email').value;
        const emailInputEl = document.querySelector('#stock_notification_input');

        emailInputEl.value = partnerEmail;
        this._handleClickStockNotificationMessage(ev);
    },

    _onClickSubmitProductStockNotificationForm: function (ev) {
        const formEl = ev.currentTarget.closest('#stock_notification_form');
        const productId = parseInt(formEl.querySelector('input[name="product_id"]').value);
        this._handleClickSubmitStockNotificationForm(ev, productId);
    },


    _handleClickStockNotificationMessage(ev) {
        ev.currentTarget.classList.add('d-none');
        ev.currentTarget.parentElement.querySelector('#stock_notification_form').classList.remove('d-none');
    },

    _handleClickSubmitStockNotificationForm(ev, productId) {
        const stockNotificationEl = ev.currentTarget.closest('#stock_notification_div');
        const formEl = stockNotificationEl.querySelector('#stock_notification_form');
        const email = stockNotificationEl.querySelector('#stock_notification_input').value.trim();

        if (!is_email(email)) {
            return this._displayEmailIncorrectMessage(stockNotificationEl);
        }

        this._rpc({
            route: "/shop/add/stock_notification",
            params: {
                product_id: productId,
                email,
            },
        }).then((data) => {
            const message = stockNotificationEl.querySelector('#stock_notification_success_message');

            message.classList.remove('d-none');
            formEl.classList.add('d-none');
        }).catch((error) => {
            this._displayEmailIncorrectMessage(stockNotificationEl);
        });
    },

    _displayEmailIncorrectMessage(stockNotificationEl) {
        const incorrectIconEl = stockNotificationEl.querySelector('#stock_notification_input_incorrect');
        incorrectIconEl.classList.remove('d-none');
    }
});

export default WebsiteSale;
