import { CustomerAddress } from '@portal/interactions/address';
import { patch } from '@web/core/utils/patch';

patch(CustomerAddress.prototype, {
    // /shop/address

    setup() {
        super.setup();
        // There is two main buttons in the DOM for mobile or desktop. User can switch from one mode
        // to the other by rotating their tablet.
        this.submitButtons = document.getElementsByName("website_sale_main_button");
        if (this.submitButtons) {
            this._boundSaveAddress = this.saveAddress.bind(this);
            this.submitButtons.forEach(
                submitButton => submitButton.addEventListener('click', this._boundSaveAddress)
            );
        }
    },

    destroy() {
        if (this.submitButtons) {
            this.submitButtons.forEach(
                submitButton => submitButton.removeEventListener('click', this._boundSaveAddress)
            );
        }
        super.destroy();
    },
});
