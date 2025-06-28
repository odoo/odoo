/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";

const CaptchaFunctionality = {
    events: {
        submit: "_onSubmit",
    },

    init() {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
    },

    async willStart() {
        return this._recaptcha.loadLibs();
    },

    _onSubmit(ev) {
        if (this._recaptcha._publicKey && !this.$el.find("input[name='recaptcha_token_response']").length) {
            ev.preventDefault();
            this._recaptcha.getToken(this.tokenName).then((tokenCaptcha) => {
                this.$el.append(
                    `<input name="recaptcha_token_response" type="hidden" value="${tokenCaptcha.token}"/>`,
                );
                this.$el.submit();
            });
        }
    },
};

publicWidget.registry.SignupCaptcha = publicWidget.Widget.extend({
    ...CaptchaFunctionality,
    selector: ".oe_signup_form",
    tokenName: "signup",
});

publicWidget.registry.ResetPasswordCaptcha = publicWidget.Widget.extend({
    ...CaptchaFunctionality,
    selector: ".oe_reset_password_form",
    tokenName: "password_reset",
});
