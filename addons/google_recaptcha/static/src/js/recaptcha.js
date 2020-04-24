odoo.define('google_recaptcha.ReCaptchaV3', function (require) {
"use strict";

const ajax = require('web.ajax');
const Class = require('web.Class');
const core = require('web.core');

const _t = core._t;

const ReCaptcha = Class.extend({
    /**
     * @override
     */
    init: function () {
        this._publicKey = odoo.reCaptchaPublicKey;
    },
    /**
     * Loads the recaptcha libraries.
     *
     * @returns {Promise|boolean} promise if libs are loading else false if the reCaptcha key is empty.
     */
    loadLibs: function () {
        if (this._publicKey) {
            this._recaptchaReady = ajax.loadJS(`https://www.recaptcha.net/recaptcha/api.js?render=${this._publicKey}`)
                .then(() => new Promise(resolve => window.grecaptcha.ready(() => resolve())));
            return this._recaptchaReady.then(() => !!document.querySelector('.grecaptcha-badge'));
        }
        return false;
    },
    /**
     * Returns an object with the token if reCaptcha call succeeds
     * If no key is set an object with a message is returned
     * If an error occured an object with the error message is returned
     *
     * @param {string} action
     * @returns {Promise|Object}
     */
    getToken: async function (action) {
        if (!this._publicKey) {
            return {
                message: _t("No recaptcha public key set."),
            };
        }
        await this._recaptchaReady;
        try {
            return {
                token: await window.grecaptcha.execute(this._publicKey, {action: action})
            };
        } catch (e) {
            return {
                error: _t("The recaptcha public key is invalid."),
            };
        }
    },
});

return {
    ReCaptcha: ReCaptcha,
};
});
