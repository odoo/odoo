/** @odoo-module alias=website_sale_stock.website_sale**/

import { WebsiteSale } from 'website_sale.website_sale';
import { is_email } from 'web.utils';
import VariantMixin from "sale.VariantMixin";

WebsiteSale.include({

    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #add_stock_email_notification_product_message': '_onClickAddStockEmailNotificationProductMessage',
        'click #add_stock_email_notification_product_form_button': '_onSubmitAddStockEmailNotificationProductForm',
    }),

    _onClickAddStockEmailNotificationProductMessage: function (ev) {
        ev.currentTarget.classList.add('d-none');
        const partnerEmail = document.querySelector('#wsale_user_email').value;
        const formEl = ev.currentTarget.parentElement.querySelector('#add_stock_email_notification_product_form');
        const emailInputEl = formEl.querySelector('input[name="email"]');

        emailInputEl.value = partnerEmail;
        formEl.classList.remove('d-none');
    },

    _onSubmitAddStockEmailNotificationProductForm: function (ev) {
        const formEl = ev.currentTarget.closest('#add_stock_email_notification_product_form');
        const productId = parseInt(formEl.querySelector('input[name="product_id"]').value);
        const email = formEl.querySelector('input[name="email"]').value.trim();
        const incorrectIconEl = formEl.querySelector('#add_stock_email_notification_product_input_incorrect');

        if (!is_email(email)) {
            incorrectIconEl.classList.remove('d-none');
            return
        }

        this._rpc({
            route: "/shop/add_stock_email_notification",
            params: {
                product_id: productId,
                email,
                displayed_in_cart: false
            },
        }).then(function (data) {
            if (data && 'error' in data){
                incorrectIconEl.classList.remove('d-none');
                return
            }
            const div = formEl.closest('#add_stock_email_notification_product_div');
            const message = div.querySelector('#add_stock_email_notification_product_success_message');

            message.classList.remove('d-none');
            formEl.classList.add('d-none');
        });
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
    }
});

export default WebsiteSale;
