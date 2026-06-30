/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { rpc } from "@web/core/network/rpc";
import { isEmail } from '@web/core/utils/strings';
<<<<<<< bab1f256eaec4c3e1a44b2bcb557d18ab2c38e5d
import VariantMixin from "@website_sale/js/sale_variant_mixin";
||||||| 1c60defdfedd4de11a18da63bec97f4c61a5dc81
=======
import { _t } from "@web/core/l10n/translation";
import { RPCError } from "@web/core/network/rpc_service";
>>>>>>> c574855859d9a874dbd5d803da328300c6ffe300

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

        rpc("/shop/add/stock_notification", {
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
<<<<<<< bab1f256eaec4c3e1a44b2bcb557d18ab2c38e5d
    },

    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination: function () {
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationStock.apply(this, arguments);
    },
    /**
     * Recomputes the combination after adding a product to the cart
     * @override
     */
    _onClickAdd(ev) {
        return this._super.apply(this, arguments).then(() => {
            if ($('div.availability_messages').length) {
                this._getCombinationInfo(ev);
            }
        });
||||||| 1c60defdfedd4de11a18da63bec97f4c61a5dc81
=======

        const errorMessageEl = stockNotificationEl.querySelector('#stock_notification_error_message');
        if (errorMessageEl) {
            errorMessageEl.textContent = message;
        } else {
            const span = document.createElement('span');
            span.id = 'stock_notification_error_message';
            span.textContent = message;
            incorrectIconEl.appendChild(span);
        }
>>>>>>> c574855859d9a874dbd5d803da328300c6ffe300
    }
});

export default WebsiteSale;
