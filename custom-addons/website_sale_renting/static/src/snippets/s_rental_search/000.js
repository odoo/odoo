/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { serializeDateTime, parseDateTime, parseDate } from "@web/core/l10n/dates";
import { RentingMixin } from '@website_sale_renting/js/renting_mixin';


publicWidget.registry.RentalSearchSnippet = publicWidget.Widget.extend(RentingMixin, {
    selector: '.s_rental_search',
    events: {
        'click .s_rental_search_btn': '_onClickRentalSearchButton',
        'toggle_search_btn .o_website_sale_daterange_picker': 'onToggleSearchBtn',
        'daterangepicker_apply': '_searchRentals',
    },

    onToggleSearchBtn(ev) {
        ev.currentTarget.querySelector('.s_rental_search_btn').disabled = Boolean(ev.detail);
    },

    _onClickRentalSearchButton(ev) {
        const parse = this._isDurationWithHours() ? parseDateTime : parseDate;
        const startInput = this.el.querySelector("input[name=renting_start_date]");
        const endInput = this.el.querySelector("input[name=renting_end_date]");
        this._searchRentals(null, {
            start_date: parse(startInput.value),
            end_date: parse(endInput.value),
        });
    },

    /**
     * This function is triggered when the user clicks on the rental search button or applies a date
     * range in the picker.
     * @param ev
     */
    _searchRentals(ev, { start_date, end_date }) {
        const searchParams = new URLSearchParams();
        if (start_date && end_date) {
            searchParams.append('start_date', `${serializeDateTime(start_date)}`);
            searchParams.append('end_date', `${serializeDateTime(end_date)}`);
        }
        const productAttributeId = this.el.querySelector('.product_attribute_search_rental_name').id;

        const productAttributeValueId = this.el.querySelector('.s_rental_search_select').value;
        if (productAttributeValueId) {
            searchParams.append('attrib', `${productAttributeId}-${productAttributeValueId}`);
        }
        window.location = `/shop?${searchParams.toString()}`;
    },
});


export default publicWidget.registry.RentalSearchSnippet;
