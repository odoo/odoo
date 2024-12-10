/** @odoo-module **/

import { uniqueId } from "@web/core/utils/functions";
import publicWidget from '@web/legacy/js/public/public_widget';
import { session } from "@web/session";
import { turnStile } from "@website_cf_turnstile/js/turnstile";


const signupTurnStile = {
    ...turnStile,
    async willStart() {
        this._super(...arguments);
        this.cleanTurnstile();
        if (
            !this.isEditable &&
            !this.el.querySelector(".s_turnstile") &&
            session.turnstile_site_key
        ) {
            this.uniq = uniqueId("turnstile_");
            const turnstileEl = this.addTurnstile(this.action);
            turnstileEl.insertBefore("button[type='submit']");
        }
    },
};

publicWidget.registry.turnstileCaptchaSignup = publicWidget.Widget.extend({
    ...signupTurnStile,
    selector: ".oe_signup_form",
    action: "signup",
});

publicWidget.registry.turnstileCaptchaPasswordReset = publicWidget.Widget.extend({
    ...signupTurnStile,
    selector: ".oe_reset_password_form",
    action: "password_reset",
});
