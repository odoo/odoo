/** @odoo-module **/

import { session } from "@web/session";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";

export class ReCaptcha {
    /**
     * @override
     */
    constructor() {
        this._publicKey = session.recaptcha_public_key;
    }
    /**
     * Loads the recaptcha libraries.
     *
     * @returns {Promise|boolean} promise if libs are loading else false if the reCaptcha key is empty.
     */
    loadLibs() {
        if (this._publicKey) {
            this._recaptchaReady = loadJS(`https://www.recaptcha.net/recaptcha/api.js?render=${encodeURIComponent(this._publicKey)}`)
                .then(() => new Promise(resolve => window.grecaptcha.ready(() => resolve())));
            return this._recaptchaReady.then(() => !!document.querySelector('.grecaptcha-badge'));
        }
        return false;
    }
    /**
     * Returns an object with the token if reCaptcha call succeeds
     * If no key is set an object with a message is returned
     * If an error occurred an object with the error message is returned
     *
     * @param {string} action
     * @returns {Promise|Object}
     */
    async getToken(action) {
        if (!this._publicKey) {
            return {
                message: _t("No recaptcha site key set."),
            };
        }
        await this._recaptchaReady;
        try {
            return {
                token: await window.grecaptcha.execute(this._publicKey, {action: action})
            };
        } catch {
            return {
                error: _t("The recaptcha site key is invalid."),
            };
        }
    }
}

export default {
    ReCaptcha: ReCaptcha,
};
