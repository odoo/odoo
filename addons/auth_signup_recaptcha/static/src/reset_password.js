/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { ReCaptcha } from '@google_recaptcha/js/recaptcha';

publicWidget.registry.ResetPasswordCaptcha = publicWidget.Widget.extend({
    selector: '.oe_reset_password_form',

    init() {
        this._super(...arguments);
        this._recaptcha = new ReCaptcha();
    },

    async willStart() {
        return this._recaptcha.loadLibs();
    },

    async start() {
        const tokenCaptcha = await this._recaptcha.getToken('portal_signup');
        this.$el.append(`<input name="recaptcha_token_response" type="hidden" value="${tokenCaptcha.token}"/>`);
    },
})
