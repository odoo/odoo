/** @odoo-module **/

import publicWidget from "web.public.widget";
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

    _onSubmit(event) {
        if (!this.$el.find("input[name='recaptcha_token_response']").length) {
            event.preventDefault();
            this._recaptcha.getToken(this.token_name).then((tokenCaptcha) => {
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
    token_name: "signup",
});

publicWidget.registry.ResetPasswordCaptcha = publicWidget.Widget.extend({
    ...CaptchaFunctionality,
    selector: ".oe_reset_password_form",
    token_name: "password_reset",
});
