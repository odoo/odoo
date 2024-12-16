/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";

publicWidget.registry.reCaptcha = publicWidget.Widget.extend({
    selector: "form[data-captcha]",
    events: {
        submit: "_onSubmit",
    },

    init() {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
    },

    async willStart() {
        this._recaptcha.loadLibs();
    },

    async _onSubmit(event) {
        const btn = this.$('button[type="submit"]');
        if (!btn.prop("disabled")) {
            btn.attr("disabled", "disabled");
            btn.prepend('<i class="fa fa-circle-o-notch fa-spin"/> ');
        }
        if (!this.$el.find("input[name='recaptcha_token_response']")[0]) {
            event.preventDefault();
            const action = this.el.dataset.captcha || "generic";
            const tokenCaptcha = await this._recaptcha.getToken(action);
            this.$el.append(
                `<input name="recaptcha_token_response" type="hidden" value="${tokenCaptcha.token}"/>`,
            );
            this.$el.submit();
        }
    },
});
