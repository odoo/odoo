/** @odoo-module **/

import publicWidget from 'web.public.widget';
import core from 'web.core'

publicWidget.registry.TermsAndConditionsCheckbox = publicWidget.Widget.extend({
        selector: 'div[name="o_checkbox_container"]',
        events: {
            'change #checkbox_tc': '_onClickTCCheckbox',
        },

        async start() {
            this.checkbox = this.el.querySelector('#checkbox_tc');
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
                core.bus.trigger('enablePaymentButton');
            } else {
                core.bus.trigger('disablePaymentButton');
            }
        },

});

export default publicWidget.registry.TermsAndConditionsCheckbox;
