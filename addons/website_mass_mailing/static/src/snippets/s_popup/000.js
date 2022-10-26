/** @odoo-module **/

import PopupWidget from 'website.s_popup';

PopupWidget.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prevents the (newsletter) popup to be shown if the user is subscribed.
     *
     * @override
     */
    _canShowPopup() {
        if (
            this.$el.is('.o_newsletter_popup') &&
            this.$el.find('input.js_subscribe_value').prop('disabled')
        ) {
            return false;
        }
        return this._super(...arguments);
    },
});

export default PopupWidget;
