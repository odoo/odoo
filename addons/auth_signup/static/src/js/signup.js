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
        const btnEl = this.el.querySelector('.oe_login_buttons > button[type="submit"]');
        btnEl.setAttribute("disabled", "disabled");
        const iTagEL = document.createElement("i");
        iTagEL.setAttribute("class", "fa fa-refresh fa-spin");
        btnEl.prepend(iTagEL);
    },
});
