/** @odoo-module **/

import { OptionalProductsModal } from "@website_sale_product_configurator/js/sale_product_configurator_modal";

OptionalProductsModal.include({

    /**
     * In Optional Product Modal, show the current_rental_price rather than the basic price.
     *
     * @override
     */
    _onChangeCombination: function (ev, $parent, combination) {
        if (combination.is_rental) {
            combination.price = combination.current_rental_price;
        }
        this._super.apply(this, arguments);
    },

    _getSerializedRentingDates() {
        const dates = this._super.apply(this, arguments) || {};
        if (this.context && !(dates.end_date || dates.start_date)) {
            dates.start_date = this.context.start_date;
            dates.end_date = this.context.end_date;
        }
        return dates;
    }
});
