import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {
    // /shop/address

    setup() {
        super.setup();
        this.submitButton = document.getElementsByName('website_sale_main_button')[0];
        if (this.submitButton) {
            this._boundSaveAddress = this.saveAddress.bind(this);
            this.submitButton.addEventListener('click', this._boundSaveAddress);
        }
    },

    destroy() {
        if (this.submitButton) {
            this.submitButton.removeEventListener('click', this._boundSaveAddress);
        }
        super.destroy();
    },
});
