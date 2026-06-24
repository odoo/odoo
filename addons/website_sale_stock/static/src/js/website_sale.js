/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { isEmail } from '@web/core/utils/strings';
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc_service";

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

        if (!isEmail(email)) {
            return this._displayErrorMessage(_t('Invalid email'), stockNotificationEl);
        }

        this.rpc("/shop/add/stock_notification", {
            product_id: productId,
            email,
        }).then((data) => {
            const message = stockNotificationEl.querySelector('#stock_notification_success_message');

            message.classList.remove('d-none');
            formEl.classList.add('d-none');
        }).catch((error) => {
            if (error instanceof RPCError) {
                this._displayErrorMessage(error.data.message, stockNotificationEl);
            } else {
                return Promise.reject(error);
            }
        });
    },

    _displayErrorMessage(message, stockNotificationEl) {
        const incorrectIconEl = stockNotificationEl.querySelector('#stock_notification_input_incorrect');
        incorrectIconEl.classList.remove('d-none');

        const errorMessageEl = stockNotificationEl.querySelector('#stock_notification_error_message');
        if (errorMessageEl) {
            errorMessageEl.textContent = message;
        } else {
            const span = document.createElement('span');
            span.id = 'stock_notification_error_message';
            span.textContent = message;
            incorrectIconEl.appendChild(span);
        }
    }
});

export default WebsiteSale;
