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
<<<<<<< saas-18.1
        const btn = this.$('.oe_login_buttons > button[type="submit"]');
        if (!btn.prop("disabled")) {
            btn.attr("disabled", "disabled");
            btn.prepend('<i class="fa fa-refresh fa-spin"/> ');
        }
||||||| 3d716002c350031216f1b955f0c1115143eeefc2
        var $btn = this.$('.oe_login_buttons > button[type="submit"]');
        $btn.attr('disabled', 'disabled');
        $btn.prepend('<i class="fa fa-refresh fa-spin"/> ');
=======
        var $btn = this.$('.oe_login_buttons > button[type="submit"]');
        if ($btn.prop("disabled")) {
            return;
        }
        $btn.attr('disabled', 'disabled');
        $btn.prepend('<i class="fa fa-refresh fa-spin"/> ');
>>>>>>> a824c6ff6397dae2a39d7c006662603a87e72224
    },
});
