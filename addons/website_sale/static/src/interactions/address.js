import { CustomerAddress } from '@portal/interactions/address';
import { patch } from '@web/core/utils/patch';
import { createElementWithContent } from '@web/core/utils/html';
import { markup } from '@odoo/owl';

patch(CustomerAddress.prototype, {
    // /shop/address

    setup() {
        super.setup();
        // There is two main buttons in the DOM for mobile or desktop. User can switch from one mode
        // to the other by rotating their tablet.
        const submitButtons = document.getElementsByName('website_sale_main_button');
        const boundSaveAddress = this.saveAddress.bind(this);
        submitButtons.forEach(submitButton => {
            submitButton.addEventListener('click', boundSaveAddress);
            this.registerCleanup(() => submitButton.removeEventListener('click', boundSaveAddress));
        });
        // Display errors as nice alerts at the top of the checkout page.
        this.errorsDiv = document.getElementById('checkout_alerts') ?? this.errorsDiv;
    },

    _renderErrorMessage(message) {
        if (!message.html) {
            return super._renderErrorMessage(...arguments);
        }
        return createElementWithContent('div', markup(message.html));
    },
});
