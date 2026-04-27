/** @odoo-module **/

import { cartHandlerMixin } from '@website_sale/js/website_sale_utils';
import { patch } from "@web/core/utils/patch";

patch(cartHandlerMixin, {
    /**
     * Override to disable the datimepicker as soon as rental product is added to cart.
     * @override
     */
    async _addToCartInPage(params) {
        const data = await super._addToCartInPage(...arguments);
        const datepickerElements = document.querySelectorAll('.o_website_sale_daterange_picker_input');
        const clearBtnElements = document.querySelectorAll('.clear-daterange');
        const infoMessageElements = document.querySelectorAll('.o_rental_info_message');
        if (data.line_id && params.start_date) {
            datepickerElements.forEach((elements) => {
                elements.disabled=true;
            });
            clearBtnElements.forEach((elements) => {
                elements.classList.add('d-none');
            });
            infoMessageElements.forEach((elements) => {
                elements.classList.remove('d-none');
            });
        }
        return data;
    },
});
