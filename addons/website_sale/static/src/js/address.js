import customerAddress from "@portal/js/address";

customerAddress.include({
    // /shop/address

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.submitButton = document.getElementsByName('website_sale_main_button')[0];
        if (this.submitButton) {
            this._boundSaveAddress = this._onSaveAddress.bind(this);
            this.submitButton.addEventListener('click', this._boundSaveAddress);
        }
    },

    destroy() {
        if (this.submitButton) {
            this.submitButton.removeEventListener("click", this._boundSaveAddress);
        }
        this._super(...arguments);
    },

});
