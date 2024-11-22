/** @odoo-module **/

import "@website/snippets/s_website_form/000";  // force deps
import publicWidget from '@web/legacy/js/public/public_widget';
import { loadJS } from '@web/core/assets';
import { session } from "@web/session";

// Rethrow the error, or we only will catch a "Script error" without any info
// because of the script api.js originating from a different domain.
window.throwTurnstileError = function throwTurnstileError(code) {
    const error = new Error("Turnstile Error");
    error.code = code;
    throw error;
};

// TODO in master, remove jQuery + re-indent this code
publicWidget.registry.s_website_form.include({
        /**
         * @override
         */
        start: function () {
            // This does not use `jsLibs` because we don't have to wait for the
            // loading before initializing the rest.
            // FIXME although, should not we prevent sending the form while this
            // this is not fully loaded yet?
            loadJS("https://challenges.cloudflare.com/turnstile/v0/api.js");

            this.cleanTurnstile();
            // TODO the first two conditions are to be removed in master
            // - the first one is always true: "isEditable" is a typo, it should
            //   be "editableMode" but also, this widget only runs outside of
            //   edit mode anyway.
            // - the second one is always true: we previously called the
            //   cleaning function anyway.
            if (!this.isEditable && !this.$('.s_turnstile').length && session.turnstile_site_key) {
                const divEl = document.createElement('div');
                divEl.classList.add('s_turnstile', 'cf-turnstile', 'float-end');
                divEl.dataset.action = 'website_form';
                divEl.dataset.appearance = new URLSearchParams(window.location.search).get('cf') === 'show'
                    ? 'always'
                    : 'interaction-only';
                divEl.dataset.responseFieldName = 'turnstile_captcha';
                divEl.dataset.sitekey = session.turnstile_site_key;
                divEl.dataset.errorCallback = 'throwTurnstileError';

                const lastEl = this.el.querySelector('.s_website_form_send, .o_website_form_send') // !compatibility
                    || this.el.children[this.el.children.length - 1];
                lastEl.after(divEl);
            }

            return this._super(...arguments);
        },

        /**
         * Remove potential existing loaded script/token
         */
        cleanTurnstile: function () {
            if (this.$('.s_turnstile').length) {
                this.$('.s_turnstile').remove();
            }
        },

        /**
         * @override
         * Discard all library changes to reset the state of the Html.
         */
        destroy: function () {
            this.cleanTurnstile();
            this._super(...arguments);
        },
});
