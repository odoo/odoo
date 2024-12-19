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
        const btn = this.$('.oe_login_buttons > button[type="submit"]');
        if (!btn.prop("disabled")) {
            btn.attr("disabled", "disabled");
            btn.prepend('<i class="fa fa-circle-o-notch fa-spin"/> ');
        }
    },
});
