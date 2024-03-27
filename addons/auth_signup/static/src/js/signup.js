/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SignUpForm = publicWidget.Widget.extend({
    selector: '.oe_signup_form',
    events: {
        'submit': '_onSubmit',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSubmit: function () {
        const btn = this.el.querySelector('.oe_login_buttons > button[type="submit"]');
        btn.setAttribute('disabled', 'disabled');
        const iTag = document.createElement('i');
        iTag.setAttribute('class', 'fa fa-refresh fa-spin');
        document.insertBefore(iTag, btn);
    },
});
