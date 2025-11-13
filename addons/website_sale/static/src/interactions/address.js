import { CustomerAddress } from '@portal/interactions/address';
import { patch } from '@web/core/utils/patch';

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
    },
});
