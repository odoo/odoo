/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";

publicWidget.registry.ResetPasswordCaptcha = publicWidget.Widget.extend({
    selector: '.oe_reset_password_form',
    events: {
        'submit': '_onSubmit',
    },

    init() {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
        this.shouldCatch = true;
    },

    async willStart() {
        return this._recaptcha.loadLibs();
    },

    _onSubmit(event) {
        if(this.shouldCatch) {
            event.preventDefault()
            this._recaptcha.getToken('portal_signup').then(tokenCaptcha => {
                this.$el.append(`<input name="recaptcha_token_response" type="hidden" value="${tokenCaptcha.token}"/>`);
                this.shouldCatch = false;
                this.$el.submit();
            })
        }
    },
})
