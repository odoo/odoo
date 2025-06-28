/** @odoo-module **/

import { Component } from '@odoo/owl';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.TermsAndConditionsCheckbox = publicWidget.Widget.extend({
        selector: 'div[name="website_sale_terms_and_conditions_checkbox"]',
        events: {
            'change #website_sale_tc_checkbox': '_onClickTCCheckbox',
        },

        async start() {
            this.checkbox = this.el.querySelector('#website_sale_tc_checkbox');
            return this._super(...arguments);
        },

        /**
         * Enable/disabled the payment button when the "Terms and Conditions" checkbox is
         * checked/unchecked.
         *
         * @private
         * @return {void}
         */
        _onClickTCCheckbox() {
            if (this.checkbox.checked) {
                Component.env.bus.trigger('enablePaymentButton');
            } else {
                Component.env.bus.trigger('disablePaymentButton');
            }
        },

});

export default publicWidget.registry.TermsAndConditionsCheckbox;
