import { rpc } from '@web/core/network/rpc';
import { isEmail } from '@web/core/utils/strings';
import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { WebsiteSale } from '@website_sale/interactions/website_sale';

patch(WebsiteSale.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            '#product_stock_notification_message': {
                't-on-click': this.onClickProductStockNotificationMessage.bind(this),
            },
            '#product_stock_notification_form_submit_button': {
                't-on-click': this.onClickSubmitProductStockNotificationForm.bind(this),
            },
        });
    },

    onClickProductStockNotificationMessage(ev) {
        const partnerEmail = document.querySelector('#wsale_user_email').value;
        const emailInputEl = document.querySelector('#stock_notification_input');

        emailInputEl.value = partnerEmail;
        this._handleClickStockNotificationMessage(ev);
    },

    onClickSubmitProductStockNotificationForm(ev) {
        const formEl = ev.currentTarget.closest('#stock_notification_form');
        const productId = parseInt(formEl.querySelector('input[name="product_id"]').value);
        this._handleClickSubmitStockNotificationForm(ev, productId);
    },

    _handleClickStockNotificationMessage(ev) {
        ev.currentTarget.classList.add('d-none');
        ev.currentTarget.parentElement.querySelector('#stock_notification_form').classList.remove('d-none');
    },

    async _handleClickSubmitStockNotificationForm(ev, productId) {
        const stockNotificationEl = ev.currentTarget.closest('#stock_notification_div');
        const formEl = stockNotificationEl.querySelector('#stock_notification_form');
        const email = stockNotificationEl.querySelector('#stock_notification_input').value.trim();

        if (!isEmail(email)) {
            return this._displayEmailIncorrectMessage(stockNotificationEl);
        }

        try {
            await this.waitFor(rpc(
                '/shop/add/stock_notification', { product_id: productId, email }
            ));
        } catch {
            this._displayEmailIncorrectMessage(stockNotificationEl);
            return;
        }
        const message = stockNotificationEl.querySelector('#stock_notification_success_message');
        message.classList.remove('d-none');
        formEl.classList.add('d-none');
    },

    _displayEmailIncorrectMessage(stockNotificationEl) {
        const incorrectIconEl = stockNotificationEl.querySelector('#stock_notification_input_incorrect');
        incorrectIconEl.classList.remove('d-none');
    },

    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination(ev, parent, combination) {
        super._onChangeCombination(...arguments);
        this._onChangeCombinationStock(...arguments);
    },

    /**
     * Recomputes the combination after adding a product to the cart
     */
    async onClickAdd(ev) {
        const quantity = await this.waitFor(super.onClickAdd(...arguments));
        if (this.el.querySelector('div.availability_messages')) {
            await this.waitFor(this._getCombinationInfo(ev));
        }
        return quantity;
    },
});
