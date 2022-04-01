/** @odoo-module **/

import WebsiteSale from 'website_sale_stock.website_sale';
import { is_email } from 'web.utils';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'click #add_stock_email_notification_wishlist_button': '_onClickAddStockEmailNotificationWishlistMessage',
        'click #add_stock_email_notification_wishlist_form_button': '_onSubmitAddStockEmailNotificationWishlistForm',
    }),

    _onClickAddStockEmailNotificationWishlistMessage: function (ev) {
        //hide the message, display the input box
        ev.currentTarget.classList.add('d-none');
        const formEl = ev.currentTarget.parentElement.querySelector('#add_stock_email_notification_wishlist_form');
        formEl.classList.remove('d-none');
    },

    _onSubmitAddStockEmailNotificationWishlistForm: function (ev) {
        const formEl = ev.currentTarget.closest('#add_stock_email_notification_wishlist_form');
        const productId = JSON.parse(ev.currentTarget.closest('tr').getAttribute('data-product-tracking-info')).item_id;
        const email = formEl.querySelector('input[name="email"]').value;
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
                displayed_in_cart: true
            },
        }).then(function (data) {
            if (data && 'error' in data){
                incorrectIconEl.classList.remove('d-none');
                return
            }
            const div = formEl.closest('#add_stock_email_notification_wishlist_div');
            const message = div.querySelector('#add_stock_email_notification_wishlist_success_message');

            message.classList.remove('d-none');
            formEl.classList.add('d-none')
        });
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Addition to the website_sale_wishlist function.
     *
     */
    _productAddedToWishlist: function () {
        this._super(...arguments);
        this._displayAddedToWishlistAlert()
    },

    _displayAddedToWishlistAlert: function () {
        const saveForLaterButtonEl = document.querySelector('#wsale_save_for_later_button');
        const addedToYourWishListAlertEl = document.querySelector('#wsale_added_to_your_wishlist_alert');
        if (saveForLaterButtonEl) {
            saveForLaterButtonEl.classList.add('d-none');
            addedToYourWishListAlertEl.classList.remove('d-none');
        }
    }
});
