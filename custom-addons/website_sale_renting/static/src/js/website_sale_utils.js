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
        if (data.line_id && params.start_date) {
            document.querySelector("input[name=renting_start_date]").disabled = true;
            document.querySelector("input[name=renting_end_date]").disabled = true;
        }
        return data;
    },
});
